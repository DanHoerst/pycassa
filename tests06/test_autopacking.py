from pycassa import ConnectionPool, ColumnFamily, NotFoundException
from pycassa.util import *
from pycassa.system_manager import *

from nose.tools import assert_raises, assert_equal, assert_almost_equal

from datetime import datetime
from uuid import uuid1
import uuid
import unittest
import time

TIME1 = uuid.UUID(hex='ddc6118e-a003-11df-8abf-00234d21610a')
TIME2 = uuid.UUID(hex='40ad6d4c-a004-11df-8abf-00234d21610a')
TIME3 = uuid.UUID(hex='dc3d5234-a00b-11df-8abf-00234d21610a')

VALS = ['val1', 'val2', 'val3']
KEYS = ['key1', 'key2', 'key3']

TEST_KS = 'PycassaTestKeyspace'

def setup_module():
    global pool
    credentials = {'username': 'jsmith', 'password': 'havebadpass'}
    pool = ConnectionPool(TEST_KS, pool_size=10, credentials=credentials,
                          framed_transport=False, timeout=15)

def teardown_module():
    pool.dispose()

class TestCFs(unittest.TestCase):

    @classmethod
    def setup_class(cls):
        sys = SystemManager()
        sys.create_column_family(TEST_KS, 'StdLong', comparator_type=LONG_TYPE)
        sys.create_column_family(TEST_KS, 'StdInteger', comparator_type=INT_TYPE)
        sys.create_column_family(TEST_KS, 'StdTimeUUID', comparator_type=TIME_UUID_TYPE)
        sys.create_column_family(TEST_KS, 'StdLexicalUUID', comparator_type=LEXICAL_UUID_TYPE)
        sys.create_column_family(TEST_KS, 'StdAscii', comparator_type=ASCII_TYPE)
        sys.create_column_family(TEST_KS, 'StdUTF8', comparator_type=UTF8_TYPE)
        sys.create_column_family(TEST_KS, 'StdBytes', comparator_type=BYTES_TYPE)
        sys.close()

        cls.cf_long  = ColumnFamily(pool, 'StdLong')
        cls.cf_int   = ColumnFamily(pool, 'StdInteger')
        cls.cf_time  = ColumnFamily(pool, 'StdTimeUUID')
        cls.cf_lex   = ColumnFamily(pool, 'StdLexicalUUID')
        cls.cf_ascii = ColumnFamily(pool, 'StdAscii')
        cls.cf_utf8  = ColumnFamily(pool, 'StdUTF8')
        cls.cf_bytes = ColumnFamily(pool, 'StdBytes')

        cls.cfs = [cls.cf_long, cls.cf_int, cls.cf_time, cls.cf_lex,
                    cls.cf_ascii, cls.cf_utf8, cls.cf_bytes]

    def tearDown(self):
        for cf in TestCFs.cfs:
            for key, cols in cf.get_range():
                cf.remove(key)

    def make_group(self, cf, cols):
        diction = { cols[0]: VALS[0],
                    cols[1]: VALS[1],
                    cols[2]: VALS[2]}
        return { 'cf': cf, 'cols': cols, 'dict': diction}

    def test_standard_column_family(self):

        # For each data type, create a group that includes its column family,
        # a set of column names, and a dictionary that maps from the column
        # names to values.
        type_groups = []

        long_cols = [1111111111111111L,
                     2222222222222222L,
                     3333333333333333L]
        type_groups.append(self.make_group(TestCFs.cf_long, long_cols))

        int_cols = [1,2,3]
        type_groups.append(self.make_group(TestCFs.cf_int, int_cols))

        time_cols = [TIME1, TIME2, TIME3]
        type_groups.append(self.make_group(TestCFs.cf_time, time_cols))

        lex_cols = [uuid.UUID(bytes='aaa aaa aaa aaaa'),
                    uuid.UUID(bytes='bbb bbb bbb bbbb'),
                    uuid.UUID(bytes='ccc ccc ccc cccc')]
        type_groups.append(self.make_group(TestCFs.cf_lex, lex_cols))

        ascii_cols = ['aaaa', 'bbbb', 'cccc']
        type_groups.append(self.make_group(TestCFs.cf_ascii, ascii_cols))

        utf8_cols = [u'a\u0020', u'b\u0020', u'c\u0020']
        type_groups.append(self.make_group(TestCFs.cf_utf8, utf8_cols))

        bytes_cols = ['aaaa', 'bbbb', 'cccc']
        type_groups.append(self.make_group(TestCFs.cf_bytes, bytes_cols))

        # Begin the actual inserting and getting
        for group in type_groups:
            cf = group.get('cf')
            gdict = group.get('dict')
            gcols = group.get('cols')

            cf.insert(KEYS[0], gdict)
            assert_equal(cf.get(KEYS[0]), gdict)

            # Check each column individually
            for i in range(3):
                assert_equal(cf.get(KEYS[0], columns=[gcols[i]]),
                             {gcols[i]: VALS[i]})

            # Check that if we list all columns, we get the full dict
            assert_equal(cf.get(KEYS[0], columns=gcols[:]), gdict)
            # The same thing with a start and end instead
            assert_equal(cf.get(KEYS[0], column_start=gcols[0], column_finish=gcols[2]),
                         gdict)
            # A start and end that are the same
            assert_equal(cf.get(KEYS[0], column_start=gcols[0], column_finish=gcols[0]),
                         {gcols[0]: VALS[0]})

            assert_equal(cf.get_count(KEYS[0]), 3)

            # Test removing rows
            cf.remove(KEYS[0], columns=gcols[:1])
            assert_equal(cf.get_count(KEYS[0]), 2)

            cf.remove(KEYS[0], columns=gcols[1:])
            assert_equal(cf.get_count(KEYS[0]), 0)

            # Insert more than one row now
            cf.insert(KEYS[0], gdict)
            cf.insert(KEYS[1], gdict)
            cf.insert(KEYS[2], gdict)


            ### multiget() tests ###

            res = cf.multiget(KEYS[:])
            for i in range(3):
                assert_equal(res.get(KEYS[i]), gdict)

            res = cf.multiget(KEYS[2:])
            assert_equal(res.get(KEYS[2]), gdict)

            # Check each column individually
            for i in range(3):
                res = cf.multiget(KEYS[:], columns=[gcols[i]])
                for j in range(3):
                    assert_equal(res.get(KEYS[j]), {gcols[i]: VALS[i]})

            # Check that if we list all columns, we get the full dict
            res = cf.multiget(KEYS[:], columns=gcols[:])
            for j in range(3):
                assert_equal(res.get(KEYS[j]), gdict)

            # The same thing with a start and end instead
            res = cf.multiget(KEYS[:], column_start=gcols[0], column_finish=gcols[2])
            for j in range(3):
                assert_equal(res.get(KEYS[j]), gdict)

            # A start and end that are the same
            res = cf.multiget(KEYS[:], column_start=gcols[0], column_finish=gcols[0])
            for j in range(3):
                assert_equal(res.get(KEYS[j]), {gcols[0]: VALS[0]})


            ### get_range() tests ###

            res = cf.get_range(start=KEYS[0])
            for sub_res in res:
                assert_equal(sub_res[1], gdict)

            res = cf.get_range(start=KEYS[0], column_start=gcols[0], column_finish=gcols[2])
            for sub_res in res:
                assert_equal(sub_res[1], gdict)

            res = cf.get_range(start=KEYS[0], columns=gcols[:])
            for sub_res in res:
                assert_equal(sub_res[1], gdict)

class TestSuperCFs(unittest.TestCase):

    @classmethod
    def setup_class(cls):
        sys = SystemManager()
        sys.create_column_family(TEST_KS, 'SuperLong', super=True, comparator_type=LONG_TYPE)
        sys.create_column_family(TEST_KS, 'SuperInt', super=True, comparator_type=INT_TYPE)
        sys.create_column_family(TEST_KS, 'SuperTime', super=True, comparator_type=TIME_UUID_TYPE)
        sys.create_column_family(TEST_KS, 'SuperLex', super=True, comparator_type=LEXICAL_UUID_TYPE)
        sys.create_column_family(TEST_KS, 'SuperAscii', super=True, comparator_type=ASCII_TYPE)
        sys.create_column_family(TEST_KS, 'SuperUTF8', super=True, comparator_type=UTF8_TYPE)
        sys.create_column_family(TEST_KS, 'SuperBytes', super=True, comparator_type=BYTES_TYPE)
        sys.close()

        cls.cf_suplong  = ColumnFamily(pool, 'SuperLong')
        cls.cf_supint   = ColumnFamily(pool, 'SuperInt')
        cls.cf_suptime  = ColumnFamily(pool, 'SuperTime')
        cls.cf_suplex   = ColumnFamily(pool, 'SuperLex')
        cls.cf_supascii = ColumnFamily(pool, 'SuperAscii')
        cls.cf_suputf8  = ColumnFamily(pool, 'SuperUTF8')
        cls.cf_supbytes = ColumnFamily(pool, 'SuperBytes')

        cls.cfs = [cls.cf_suplong, cls.cf_supint, cls.cf_suptime,
                   cls.cf_suplex, cls.cf_supascii, cls.cf_suputf8,
                   cls.cf_supbytes]

    def tearDown(self):
        for cf in TestSuperCFs.cfs:
            for key, cols in cf.get_range():
                cf.remove(key)

    def make_super_group(self, cf, cols):
        diction = { cols[0]: {'bytes': VALS[0]},
                    cols[1]: {'bytes': VALS[1]},
                    cols[2]: {'bytes': VALS[2]}}
        return { 'cf': cf, 'cols': cols, 'dict': diction}

    def test_super_column_families(self):

        # For each data type, create a group that includes its column family,
        # a set of column names, and a dictionary that maps from the column
        # names to values.
        type_groups = []

        long_cols = [1111111111111111L,
                     2222222222222222L,
                     3333333333333333L]
        type_groups.append(self.make_super_group(TestSuperCFs.cf_suplong, long_cols))

        int_cols = [1,2,3]
        type_groups.append(self.make_super_group(TestSuperCFs.cf_supint, int_cols))

        time_cols = [TIME1, TIME2, TIME3]
        type_groups.append(self.make_super_group(TestSuperCFs.cf_suptime, time_cols))

        lex_cols = [uuid.UUID(bytes='aaa aaa aaa aaaa'),
                    uuid.UUID(bytes='bbb bbb bbb bbbb'),
                    uuid.UUID(bytes='ccc ccc ccc cccc')]
        type_groups.append(self.make_super_group(TestSuperCFs.cf_suplex, lex_cols))

        ascii_cols = ['aaaa', 'bbbb', 'cccc']
        type_groups.append(self.make_super_group(TestSuperCFs.cf_supascii, ascii_cols))

        utf8_cols = [u'a\u0020', u'b\u0020', u'c\u0020']
        type_groups.append(self.make_super_group(TestSuperCFs.cf_suputf8, utf8_cols))

        bytes_cols = ['aaaa', 'bbbb', 'cccc']
        type_groups.append(self.make_super_group(TestSuperCFs.cf_supbytes, bytes_cols))

        # Begin the actual inserting and getting
        for group in type_groups:
            cf = group.get('cf')
            gdict = group.get('dict')
            gcols = group.get('cols')

            cf.insert(KEYS[0], gdict)
            assert_equal(cf.get(KEYS[0]), gdict)

            # Check each supercolumn individually
            for i in range(3):
                res = cf.get(KEYS[0], columns=[gcols[i]])
                assert_equal(res, {gcols[i]: {'bytes': VALS[i]}})

            # Check that if we list all columns, we get the full dict
            assert_equal(cf.get(KEYS[0], columns=gcols[:]), gdict)
            # The same thing with a start and end instead
            assert_equal(cf.get(KEYS[0], column_start=gcols[0], column_finish=gcols[2]), gdict)
            # A start and end that are the same
            assert_equal(cf.get(KEYS[0], column_start=gcols[0], column_finish=gcols[0]),
                         {gcols[0]: {'bytes': VALS[0]}})

            assert_equal(cf.get_count(KEYS[0]), 3)

            # Test removing rows
            cf.remove(KEYS[0], columns=gcols[:1])
            assert_equal(cf.get_count(KEYS[0]), 2)

            cf.remove(KEYS[0], columns=gcols[1:])
            assert_equal(cf.get_count(KEYS[0]), 0)

            # Insert more than one row now
            cf.insert(KEYS[0], gdict)
            cf.insert(KEYS[1], gdict)
            cf.insert(KEYS[2], gdict)


            ### multiget() tests ###

            res = cf.multiget(KEYS[:])
            for i in range(3):
                assert_equal(res.get(KEYS[i]), gdict)

            res = cf.multiget(KEYS[2:])
            assert_equal(res.get(KEYS[2]), gdict)

            # Check each column individually
            for i in range(3):
                res = cf.multiget(KEYS[:], columns=[gcols[i]])
                for j in range(3):
                    assert_equal(res.get(KEYS[j]), {gcols[i]: {'bytes': VALS[i]}})

            # Check that if we list all columns, we get the full dict
            res = cf.multiget(KEYS[:], columns=gcols[:])
            for j in range(3):
                assert_equal(res.get(KEYS[j]), gdict)

            # The same thing with a start and end instead
            res = cf.multiget(KEYS[:], column_start=gcols[0], column_finish=gcols[2])
            for j in range(3):
                assert_equal(res.get(KEYS[j]), gdict)

            # A start and end that are the same
            res = cf.multiget(KEYS[:], column_start=gcols[0], column_finish=gcols[0])
            for j in range(3):
                assert_equal(res.get(KEYS[j]), {gcols[0]: {'bytes': VALS[0]}})


            ### get_range() tests ###

            res = cf.get_range(start=KEYS[0])
            for sub_res in res:
                assert_equal(sub_res[1], gdict)

            res = cf.get_range(start=KEYS[0], column_start=gcols[0], column_finish=gcols[2])
            for sub_res in res:
                assert_equal(sub_res[1], gdict)

            res = cf.get_range(start=KEYS[0], columns=gcols[:])
            for sub_res in res:
                assert_equal(sub_res[1], gdict)

class TestSuperSubCFs(unittest.TestCase):

    @classmethod
    def setup_class(cls):
        sys = SystemManager()
        sys.create_column_family(TEST_KS, 'SuperLongSubLong', super=True,
                                 comparator_type=LONG_TYPE, subcomparator_type=LONG_TYPE)
        sys.create_column_family(TEST_KS, 'SuperLongSubInt', super=True,
                                 comparator_type=LONG_TYPE, subcomparator_type=INT_TYPE)
        sys.create_column_family(TEST_KS, 'SuperLongSubTime', super=True,
                                 comparator_type=LONG_TYPE, subcomparator_type=TIME_UUID_TYPE)
        sys.create_column_family(TEST_KS, 'SuperLongSubLex', super=True,
                                 comparator_type=LONG_TYPE, subcomparator_type=LEXICAL_UUID_TYPE)
        sys.create_column_family(TEST_KS, 'SuperLongSubAscii', super=True,
                                 comparator_type=LONG_TYPE, subcomparator_type=ASCII_TYPE)
        sys.create_column_family(TEST_KS, 'SuperLongSubUTF8', super=True,
                                 comparator_type=LONG_TYPE, subcomparator_type=UTF8_TYPE)
        sys.create_column_family(TEST_KS, 'SuperLongSubBytes', super=True,
                                 comparator_type=LONG_TYPE, subcomparator_type=BYTES_TYPE)
        sys.close()

        cls.cf_suplong_sublong  = ColumnFamily(pool, 'SuperLongSubLong')
        cls.cf_suplong_subint   = ColumnFamily(pool, 'SuperLongSubInt')
        cls.cf_suplong_subtime  = ColumnFamily(pool, 'SuperLongSubTime')
        cls.cf_suplong_sublex   = ColumnFamily(pool, 'SuperLongSubLex')
        cls.cf_suplong_subascii = ColumnFamily(pool, 'SuperLongSubAscii')
        cls.cf_suplong_subutf8  = ColumnFamily(pool, 'SuperLongSubUTF8')
        cls.cf_suplong_subbytes = ColumnFamily(pool, 'SuperLongSubBytes')

        cls.cfs = [cls.cf_suplong_subint, cls.cf_suplong_subint,
                   cls.cf_suplong_subtime, cls.cf_suplong_sublex,
                   cls.cf_suplong_subascii, cls.cf_suplong_subutf8,
                   cls.cf_suplong_subbytes]

    def tearDown(self):
        for cf in TestSuperSubCFs.cfs:
            for key, cols in cf.get_range():
                cf.remove(key)

    def make_sub_group(self, cf, cols):
        diction = {123L: {cols[0]: VALS[0],
                          cols[1]: VALS[1],
                          cols[2]: VALS[2]}}
        return { 'cf': cf, 'cols': cols, 'dict': diction}

    def test_super_column_family_subs(self):

        # For each data type, create a group that includes its column family,
        # a set of column names, and a dictionary that maps from the column
        # names to values.
        type_groups = []

        long_cols = [1111111111111111L,
                     2222222222222222L,
                     3333333333333333L]
        type_groups.append(self.make_sub_group(TestSuperSubCFs.cf_suplong_sublong, long_cols))

        int_cols = [1,2,3]
        type_groups.append(self.make_sub_group(TestSuperSubCFs.cf_suplong_subint, int_cols))

        time_cols = [TIME1, TIME2, TIME3]
        type_groups.append(self.make_sub_group(TestSuperSubCFs.cf_suplong_subtime, time_cols))

        lex_cols = [uuid.UUID(bytes='aaa aaa aaa aaaa'),
                    uuid.UUID(bytes='bbb bbb bbb bbbb'),
                    uuid.UUID(bytes='ccc ccc ccc cccc')]
        type_groups.append(self.make_sub_group(TestSuperSubCFs.cf_suplong_sublex, lex_cols))

        ascii_cols = ['aaaa', 'bbbb', 'cccc']
        type_groups.append(self.make_sub_group(TestSuperSubCFs.cf_suplong_subascii, ascii_cols))

        utf8_cols = [u'a\u0020', u'b\u0020', u'c\u0020']
        type_groups.append(self.make_sub_group(TestSuperSubCFs.cf_suplong_subutf8, utf8_cols))

        bytes_cols = ['aaaa', 'bbbb', 'cccc']
        type_groups.append(self.make_sub_group(TestSuperSubCFs.cf_suplong_subbytes, bytes_cols))

        # Begin the actual inserting and getting
        for group in type_groups:
            cf = group.get('cf')
            gdict = group.get('dict')

            cf.insert(KEYS[0], gdict)

            assert_equal(cf.get(KEYS[0]), gdict)
            assert_equal(cf.get(KEYS[0], columns=[123L]), gdict)

            # A start and end that are the same
            assert_equal(cf.get(KEYS[0], column_start=123L, column_finish=123L), gdict)

            assert_equal(cf.get_count(KEYS[0]), 1)

            # Test removing rows
            cf.remove(KEYS[0], super_column=123L)
            assert_equal(cf.get_count(KEYS[0]), 0)

            # Insert more than one row now
            cf.insert(KEYS[0], gdict)
            cf.insert(KEYS[1], gdict)
            cf.insert(KEYS[2], gdict)


            ### multiget() tests ###

            res = cf.multiget(KEYS[:])
            for i in range(3):
                assert_equal(res.get(KEYS[i]), gdict)

            res = cf.multiget(KEYS[2:])
            assert_equal(res.get(KEYS[2]), gdict)

            res = cf.multiget(KEYS[:], columns=[123L])
            for i in range(3):
                assert_equal(res.get(KEYS[i]), gdict)

            res = cf.multiget(KEYS[:], super_column=123L)
            for i in range(3):
                assert_equal(res.get(KEYS[i]), gdict.get(123L))

            res = cf.multiget(KEYS[:], column_start=123L, column_finish=123L)
            for j in range(3):
                assert_equal(res.get(KEYS[j]), gdict)

            ### get_range() tests ###

            res = cf.get_range(start=KEYS[0])
            for sub_res in res:
                assert_equal(sub_res[1], gdict)

            res = cf.get_range(start=KEYS[0], column_start=123L, column_finish=123L)
            for sub_res in res:
                assert_equal(sub_res[1], gdict)

            res = cf.get_range(start=KEYS[0], columns=[123L])
            for sub_res in res:
                assert_equal(sub_res[1], gdict)

            res = cf.get_range(start=KEYS[0], super_column=123L)
            for sub_res in res:
                assert_equal(sub_res[1], gdict.get(123L))

class TestTimeUUIDs(unittest.TestCase):

    def setUp(self):
        self.cf_time = ColumnFamily(pool, 'StdTimeUUID')

    def tearDown(self):
        self.cf_time.remove('key1')

    def test_datetime_to_uuid(self):
        key = 'key1'
        timeline = []

        timeline.append(datetime.now())
        time1 = uuid1()
        col1 = {time1:'0'}
        self.cf_time.insert(key, col1)
        time.sleep(1)

        timeline.append(datetime.now())
        time2 = uuid1()
        col2 = {time2:'1'}
        self.cf_time.insert(key, col2)
        time.sleep(1)

        timeline.append(datetime.now())

        cols = {time1:'0', time2:'1'}

        assert_equal(self.cf_time.get(key, column_start=timeline[0])                            , cols)
        assert_equal(self.cf_time.get(key,                           column_finish=timeline[2]) , cols)
        assert_equal(self.cf_time.get(key, column_start=timeline[0], column_finish=timeline[2]) , cols)
        assert_equal(self.cf_time.get(key, column_start=timeline[0], column_finish=timeline[2]) , cols)
        assert_equal(self.cf_time.get(key, column_start=timeline[0], column_finish=timeline[1]) , col1)
        assert_equal(self.cf_time.get(key, column_start=timeline[1], column_finish=timeline[2]) , col2)

    def test_time_to_uuid(self):
        key = 'key1'
        timeline = []

        timeline.append(time.time())
        time1 = uuid1()
        col1 = {time1:'0'}
        self.cf_time.insert(key, col1)
        time.sleep(0.1)

        timeline.append(time.time())
        time2 = uuid1()
        col2 = {time2:'1'}
        self.cf_time.insert(key, col2)
        time.sleep(0.1)

        timeline.append(time.time())

        cols = {time1:'0', time2:'1'}

        assert_equal(self.cf_time.get(key, column_start=timeline[0])                            , cols)
        assert_equal(self.cf_time.get(key,                           column_finish=timeline[2]) , cols)
        assert_equal(self.cf_time.get(key, column_start=timeline[0], column_finish=timeline[2]) , cols)
        assert_equal(self.cf_time.get(key, column_start=timeline[0], column_finish=timeline[2]) , cols)
        assert_equal(self.cf_time.get(key, column_start=timeline[0], column_finish=timeline[1]) , col1)
        assert_equal(self.cf_time.get(key, column_start=timeline[1], column_finish=timeline[2]) , col2)

    def test_auto_time_to_uuid1(self):
        key = 'key1'
        t = time.time()
        col = {t: 'foo'}
        self.cf_time.insert(key, col)
        uuid_res = self.cf_time.get(key).keys()[0]
        timestamp = convert_uuid_to_time(uuid_res)
        assert_almost_equal(timestamp, t, places=3)

class TestTypeErrors(unittest.TestCase):

    def test_packing_enabled(self):
        self.cf = ColumnFamily(pool, 'Standard1')
        self.cf.insert('key', {'col': 'val'})
        assert_raises(TypeError, self.cf.insert, args=('key', {123: 'val'}))
        assert_raises(TypeError, self.cf.insert, args=('key', {'col': 123}))
        assert_raises(TypeError, self.cf.insert, args=('key', {123: 123}))
        self.cf.remove('key')

    def test_packing_disabled(self):
        self.cf = ColumnFamily(pool, 'Standard1', autopack_names=False, autopack_values=False)
        self.cf.insert('key', {'col': 'val'})
        assert_raises(TypeError, self.cf.insert, args=('key', {123: 'val'}))
        assert_raises(TypeError, self.cf.insert, args=('key', {'col': 123}))
        assert_raises(TypeError, self.cf.insert, args=('key', {123: 123}))
        self.cf.remove('key')
