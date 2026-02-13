import unittest
from unittest.mock import patch, MagicMock
from api_clients import search_itunes, search_deezer_artists, get_lastfm_artist_data

class TestApiClients(unittest.TestCase):
    @patch('api_clients.requests.get')
    def test_search_itunes(self, mock_get):
        # Mocking iTunes response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'results': [{'artistName': 'Queen', 'artistId': 123}]
        }
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        results = search_itunes('Queen', 'musicArtist', 1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['artistName'], 'Queen')
        mock_get.assert_called_once()

    @patch('api_clients.requests.get')
    def test_search_deezer_artists(self, mock_get):
        # Mocking Deezer response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'data': [
                {'id': 1, 'name': 'Queen', 'nb_fan': 1500000, 'picture_xl': 'http://image.jpg'}
            ]
        }
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        results = search_deezer_artists('Queen', 1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['artistName'], 'Queen')
        self.assertIn('1.5M', results[0]['stats'])
        self.assertEqual(results[0]['image'], 'http://image.jpg')

    @patch('api_clients.requests.get')
    def test_get_lastfm_artist_data(self, mock_get):
        # Mocking Last.fm response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'artist': {
                'stats': {'listeners': '1000000'},
                'bio': {'summary': 'Bio text <a href="..."></a>'},
                'tags': {'tag': [{'name': 'Rock'}]}
            }
        }
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        data = get_lastfm_artist_data('Queen')
        self.assertIsNotNone(data)
        self.assertIn('1000K', data['stats']) # 1000000 is not > 1000000 in the current logic
        self.assertEqual(data['bio'], 'Bio text')
        self.assertEqual(data['tags'], ['Rock'])

if __name__ == '__main__':
    unittest.main()
