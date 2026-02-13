import unittest
from utils import clean_name, normalize_title, sort_albums

class TestUtils(unittest.TestCase):
    def test_clean_name(self):
        self.assertEqual(clean_name("In Rock (2018 Remastered Version)"), "In Rock")
        self.assertEqual(clean_name("Deep Purple In Rock (Remastered)"), "Deep Purple In Rock")
        self.assertEqual(clean_name("Album Name - Deluxe Edition"), "Album Name")
        self.assertEqual(clean_name("Normal Album"), "Normal Album")
        self.assertEqual(clean_name(""), "")
        self.assertEqual(clean_name(None), "")

    def test_normalize_title(self):
        self.assertEqual(normalize_title("Let It Be (Remastered)"), "letitbe")
        self.assertEqual(normalize_title("Hello-World! 123"), "helloworld123")
        self.assertEqual(normalize_title("  Space  "), "space")
        self.assertEqual(normalize_title(""), "")
        self.assertEqual(normalize_title(None), "")

    def test_sort_albums(self):
        albums = [
            {'collectionName': 'Album A', 'releaseDate': '2020-01-01T00:00:00Z', 'trackCount': 10},
            {'collectionName': 'Single B', 'releaseDate': '2021-01-01T00:00:00Z', 'trackCount': 2},
            {'collectionName': 'Album A (Reissue)', 'releaseDate': '2022-01-01T00:00:00Z', 'trackCount': 10},
            {'collectionName': 'Live in London', 'releaseDate': '2019-01-01T00:00:00Z', 'trackCount': 15},
            {'collectionName': 'Greatest Hits', 'releaseDate': '2023-01-01T00:00:00Z', 'trackCount': 20},
        ]
        sorted_cats = sort_albums(albums)
        
        # Check categories
        self.assertEqual(len(sorted_cats['albums']), 1)
        self.assertEqual(sorted_cats['albums'][0]['collectionName'], 'Album A')
        self.assertEqual(sorted_cats['albums'][0]['year'], '2020') # Deduplication should keep earlier date
        
        self.assertEqual(len(sorted_cats['singles']), 1)
        self.assertEqual(sorted_cats['singles'][0]['collectionName'], 'Single B')
        
        self.assertEqual(len(sorted_cats['live']), 1)
        self.assertEqual(sorted_cats['live'][0]['collectionName'], 'Live in London')
        
        self.assertEqual(len(sorted_cats['compilations']), 1)
        self.assertEqual(sorted_cats['compilations'][0]['collectionName'], 'Greatest Hits')

if __name__ == '__main__':
    unittest.main()
