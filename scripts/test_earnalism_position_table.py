"""Portable positional fakes only; no ML imports or runtime qualification."""
import contextlib
import hashlib
import struct
import types
import unittest

from scripts.earnalism_voice_runtime import position_table as p


class Tensor:
    def __init__(self,rows,*,parent=None,indices=None):
        self.rows=rows;self.parent=parent;self.indices=indices
        self.dtype='float32';self.device='cpu';self.requires_grad=False
    @property
    def shape(self):return (len(self.rows),len(self.rows[0]))
    def detach(self):return self
    def to(self,**kwargs):self.dtype=kwargs['dtype'];self.device=kwargs['device'];return self
    def __getitem__(self,key):
        indices=list(range(len(self.rows)))[key]
        return Tensor([self.rows[i] for i in indices],parent=self,indices=indices)
    def copy_(self,other):
        for index,row in zip(self.indices,other.rows):self.parent.rows[index]=list(row)
        self.rows=[self.parent.rows[i] for i in self.indices]


class ParlerTTSSinusoidalPositionalEmbedding:
    embedding_dim=2
    def __init__(self):
        # Deliberately differ from recomputation, including signed zero. The
        # implementation must preserve the stored prefix, not approximate it.
        self.weights=Tensor([[-0.0,123.0]]+[[10000.0+i,-i] for i in range(1,4096)])
        self.before_get=lambda:None
    def get_embedding(self,num_embeddings,embedding_dim):
        self.before_get()
        return Tensor([[float(i),-float(i)] for i in range(num_embeddings)])


def tensor_digest(values):
    h=hashlib.sha256()
    for name,value in sorted(values.items()):
        h.update((name+str(value.shape)+value.dtype).encode())
        for row in value.rows:
            for x in row:h.update(struct.pack('<f',x))
    return h.hexdigest()


class PositionTests(unittest.TestCase):
    def setUp(self):
        pos=ParlerTTSSinusoidalPositionalEmbedding()
        self.model=types.SimpleNamespace(decoder=types.SimpleNamespace(model=types.SimpleNamespace(decoder=types.SimpleNamespace(embed_positions=pos))),
            config=types.SimpleNamespace(decoder=types.SimpleNamespace(rope_embeddings=False)),remaining='unchanged')
        def parameter(value,requires_grad):value.requires_grad=requires_grad;return value
        self.torch=types.SimpleNamespace(float32='float32',get_default_dtype=lambda:'float32',no_grad=contextlib.nullcontext,nn=types.SimpleNamespace(Parameter=parameter))
        self.frozen=lambda model,exclude:{'sha256':model.remaining,'excluded':sorted(exclude)}
    def prepare(self,**kwargs):
        return p.prepare_position_table(self.model,self.torch,required_positions=8200,trainable_names={'decoder.layer23.target'},tensor_digest=tensor_digest,frozen_digest=self.frozen,**kwargs)

    def test_original_prefix_bits_and_cached8000_positions_are_preserved(self):
        original=tensor_digest({p.POSITION_NAME:self.model.decoder.model.decoder.embed_positions.weights})
        report=self.prepare();pos=self.model.decoder.model.decoder.embed_positions
        self.assertEqual(pos.weights.shape,(16384,2));self.assertEqual(report['original_prefix_tensor_sha256'],original)
        self.assertEqual(tensor_digest({p.POSITION_NAME:pos.weights[:4096]}),original)
        self.assertEqual(pos.weights.rows[8000],[8000.0,-8000.0]);self.assertFalse(pos.weights.requires_grad)
        self.assertTrue(p.verify_position_table(self.model,report,tensor_digest=tensor_digest))

    def test_prefix_suffix_and_gradient_mutations_are_detected_later(self):
        report=self.prepare();pos=self.model.decoder.model.decoder.embed_positions
        pos.weights.rows[0][0]=+0.0
        with self.assertRaisesRegex(ValueError,'prefix changed'):p.verify_position_table(self.model,report,tensor_digest=tensor_digest)
        self.setUp();report=self.prepare();pos=self.model.decoder.model.decoder.embed_positions;pos.weights.rows[12000][0]+=1
        with self.assertRaises(ValueError):p.verify_position_table(self.model,report,tensor_digest=tensor_digest)
        self.setUp();report=self.prepare();self.model.decoder.model.decoder.embed_positions.weights.requires_grad=True
        with self.assertRaisesRegex(ValueError,'gradient changed'):p.verify_position_table(self.model,report,tensor_digest=tensor_digest)

    def test_remaining_frozen_state_and_scope_overflow_are_checked(self):
        self.model.decoder.model.decoder.embed_positions.before_get=lambda:setattr(self.model,'remaining','changed')
        with self.assertRaisesRegex(ValueError,'Other frozen state'):self.prepare()
        self.setUp()
        with self.assertRaisesRegex(ValueError,'16384 capacity'):
            p.prepare_position_table(self.model,self.torch,required_positions=16385,trainable_names=set(),tensor_digest=tensor_digest,frozen_digest=self.frozen)
        self.assertEqual(self.model.decoder.model.decoder.embed_positions.weights.shape,(4096,2))



if __name__=='__main__':unittest.main()
