"""Deterministic positional preparation for the exact pinned Parler class.

No imports of torch or model packages. The admitted native backend supplies the
actual torch module, exact class and already-bound digest helpers. Preparation
uses the pinned get_embedding API, copies the original prefix bit-for-bit, and
verifies every other frozen state entry before/after the sole table assignment.
"""

POSITION_NAME = 'decoder.model.decoder.embed_positions.weights'
ORIGINAL_POSITIONS = 4096
CAPACITY = 16384


def _position(model):
    positional = model.decoder.model.decoder.embed_positions
    if type(positional).__name__ != 'ParlerTTSSinusoidalPositionalEmbedding':
        raise ValueError('Exact pinned sinusoidal positional class required')
    if getattr(model.config.decoder,'rope_embeddings',None) is not False:
        raise ValueError('No RoPE/architecture substitution permitted')
    return positional


def prepare_position_table(model,torch,*,required_positions,capacity=CAPACITY,
                           trainable_names,tensor_digest,frozen_digest):
    """Call once per fresh model, before either phase's frozen-state snapshot."""
    if type(required_positions) is not int or not 0 < required_positions <= capacity or capacity != CAPACITY:
        raise ValueError('Proposed complete prompt/cache positions exceed fixed16384 capacity')
    positional = _position(model); original = positional.weights
    if (len(original.shape) != 2 or original.shape[0] != ORIGINAL_POSITIONS
            or original.shape[1] != positional.embedding_dim or original.dtype != torch.float32
            or original.requires_grad or torch.get_default_dtype() != torch.float32):
        raise ValueError('Exact original4096 frozen FP32 table required')
    exclude = set(trainable_names)|{POSITION_NAME}
    remaining_before = frozen_digest(model,exclude)
    prefix_before = tensor_digest({POSITION_NAME:original})
    with torch.no_grad():
        # The exact source API returns deterministic sinusoidal rows. Preserve
        # every original stored bit, including platform rounding/signed zero,
        # rather than replace the base prefix with recomputed approximations.
        prepared = positional.get_embedding(capacity,positional.embedding_dim).to(
            device=original.device,dtype=original.dtype)
        prepared[:ORIGINAL_POSITIONS].copy_(original.detach())
        positional.weights = torch.nn.Parameter(prepared,requires_grad=False)
    prefix_after = tensor_digest({POSITION_NAME:positional.weights[:ORIGINAL_POSITIONS]})
    if prefix_after != prefix_before: raise ValueError('Original positional prefix changed')
    remaining_after = frozen_digest(model,exclude)
    if remaining_after != remaining_before: raise ValueError('Other frozen state changed during deterministic positional preparation')
    report = {'schema':'earnalism.exact_positional_preparation.v1','class':type(positional).__name__,
        'parameter':POSITION_NAME,'original_positions':ORIGINAL_POSITIONS,'capacity':capacity,
        'required_positions':required_positions,'embedding_dim':positional.embedding_dim,
        'dtype':str(positional.weights.dtype),'requires_grad':False,
        'original_prefix_tensor_sha256':prefix_before,
        'prepared_table_tensor_sha256':tensor_digest({POSITION_NAME:positional.weights}),
        'remaining_frozen_state':remaining_after,'original_prefix_bit_identical':True,
        'other_frozen_state_unchanged':True,'method':'PINNED_GET_EMBEDDING_PLUS_EXACT_STORED_PREFIX_COPY',
        'learned_parameter_family_changed':False,'rope_or_configuration_changed':False}
    verify_position_table(model,report,tensor_digest=tensor_digest)
    return report


def verify_position_table(model,report,*,tensor_digest):
    """Verify immutable prepared table at subsequent training/inference snapshots."""
    positional = _position(model); weights = positional.weights
    if (tuple(weights.shape) != (report['capacity'],report['embedding_dim'])
            or str(weights.dtype) != report['dtype'] or weights.requires_grad):
        raise ValueError('Prepared frozen positional table shape/dtype/gradient changed')
    if (tensor_digest({POSITION_NAME:weights[:report['original_positions']]}) != report['original_prefix_tensor_sha256']
            or tensor_digest({POSITION_NAME:weights}) != report['prepared_table_tensor_sha256']):
        raise ValueError('Prepared positional table/prefix changed after initialization')
    return True
