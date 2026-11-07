import array, unittest
from audio_review import splice, db

class SpliceReviewTests(unittest.TestCase):
    def test_silent_stereo_join_has_no_sample_jump(self):
        result=splice(array.array('h',[0]*400),100,2,1)
        self.assertIsNone(result['sample_jump_dbfs'])
        self.assertIsNone(result['before_200ms_rms_dbfs'])
    def test_stereo_jump_is_measured_per_channel(self):
        a=array.array('h',[0]*200+[16384,-8192]*100)
        result=splice(a,100,2,1)
        self.assertAlmostEqual(result['sample_jump_dbfs'],-6.021,places=3)
        self.assertAlmostEqual(result['after_200ms_rms_dbfs'],-8.062,places=3)
    def test_outside_join_is_rejected(self):
        with self.assertRaises(ValueError):splice(array.array('h',[0]*10),100,2,0)

if __name__=='__main__':unittest.main()
