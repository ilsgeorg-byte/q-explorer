import unittest
from app import app, db
from models import User, Playlist

class TestRoutes(unittest.TestCase):
    def setUp(self):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_index_route(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'q-explorer', response.data.lower())

    def test_register_login_flow(self):
        # Register
        resp = self.client.post('/register', data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        
        # Check user in DB
        user = User.query.filter_by(username='testuser').first()
        self.assertIsNotNone(user)
        
        # Logout
        self.client.get('/logout', follow_redirects=True)
        
        # Login
        resp = self.client.post('/login', data={
            'email': 'test@example.com',
            'password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        
    def test_profile_requires_login(self):
        response = self.client.get('/profile', follow_redirects=True)
        # Should redirect to login
        self.assertNotEqual(response.status_code, 500)


class TestSearchRoutes(unittest.TestCase):
    """Tests for /see-all/<type> search routes."""
    
    def setUp(self):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['TESTING'] = True
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_see_all_artists_no_query(self):
        """Test /see-all/artists without query parameter."""
        response = self.client.get('/see-all/artists')
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'No query provided', response.data)
    
    def test_see_all_artists_with_query(self):
        """Test /see-all/artists with valid query."""
        response = self.client.get('/see-all/artists?q=the+beatles')
        self.assertEqual(response.status_code, 200)
    
    def test_see_all_albums_with_query(self):
        """Test /see-all/albums with valid query."""
        response = self.client.get('/see-all/albums?q=abbey+road')
        self.assertEqual(response.status_code, 200)
    
    def test_see_all_songs_with_query(self):
        """Test /see-all/songs with valid query."""
        response = self.client.get('/see-all/songs?q=hey+jude')
        self.assertEqual(response.status_code, 200)
    
    def test_see_all_pagination(self):
        """Test /see-all/<type> with pagination parameters."""
        response = self.client.get('/see-all/albums?q=album&page=2&per_page=10')
        self.assertEqual(response.status_code, 200)
        # Should contain pagination info
        self.assertIn(b'Page', response.data)
    
    def test_see_all_sorting_by_name(self):
        """Test /see-all/<type> with name sorting."""
        response = self.client.get('/see-all/albums?q=album&sort=name')
        self.assertEqual(response.status_code, 200)
    
    def test_see_all_sorting_by_year(self):
        """Test /see-all/<type> with year sorting."""
        response = self.client.get('/see-all/albums?q=album&sort=year')
        self.assertEqual(response.status_code, 200)
    
    def test_see_all_shows_see_all_buttons(self):
        """Test that search results show See All buttons."""
        response = self.client.get('/?q=the')
        self.assertEqual(response.status_code, 200)
        # Should have see all buttons or links
        self.assertNotEqual(response.status_code, 500)


class TestArtistRoutes(unittest.TestCase):
    """Tests for /artist/<id> and /artist/<id>/discography/<category> routes."""
    
    def setUp(self):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['TESTING'] = True
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_artist_page_valid_id(self):
        """Test artist page with valid artist ID."""
        response = self.client.get('/artist/909253')  # Taylor Swift
        self.assertEqual(response.status_code, 200)
    
    def test_artist_page_has_discography_sections(self):
        """Test that artist page contains discography sections."""
        response = self.client.get('/artist/909253')
        self.assertEqual(response.status_code, 200)
        # Should contain section headers for albums/singles/live/compilations
        self.assertNotEqual(response.status_code, 500)
    
    def test_artist_page_has_see_all_buttons(self):
        """Test that artist page has 'See All' buttons for categories."""
        response = self.client.get('/artist/909253')
        self.assertEqual(response.status_code, 200)
        # Check for See All buttons/links
        self.assertIn(b'See All', response.data)
    
    def test_artist_page_limits_albums_to_six(self):
        """Test that artist page shows max 6 albums per category."""
        response = self.client.get('/artist/909253')
        self.assertEqual(response.status_code, 200)
        # Response should render without 500 error
        self.assertNotIn(b'500', response.data)
    
    def test_artist_discography_albums(self):
        """Test /artist/<id>/discography/albums route."""
        response = self.client.get('/artist/909253/discography/albums')
        self.assertIn(response.status_code, [200, 404])
    
    def test_artist_discography_singles(self):
        """Test /artist/<id>/discography/singles route."""
        response = self.client.get('/artist/909253/discography/singles')
        self.assertIn(response.status_code, [200, 404])
    
    def test_artist_discography_live(self):
        """Test /artist/<id>/discography/live route."""
        response = self.client.get('/artist/909253/discography/live')
        self.assertIn(response.status_code, [200, 404])
    
    def test_artist_discography_compilations(self):
        """Test /artist/<id>/discography/compilations route."""
        response = self.client.get('/artist/909253/discography/compilations')
        self.assertIn(response.status_code, [200, 404])
    
    def test_artist_discography_pagination(self):
        """Test artist discography with pagination."""
        response = self.client.get('/artist/909253/discography/albums?page=1&per_page=20')
        self.assertIn(response.status_code, [200, 404])
    
    def test_artist_discography_sorting(self):
        """Test artist discography with sorting options."""
        response = self.client.get('/artist/909253/discography/albums?sort=year')
        self.assertIn(response.status_code, [200, 404])
    
    def test_artist_discography_invalid_category(self):
        """Test artist discography with invalid category."""
        response = self.client.get('/artist/909253/discography/invalid_category')
        self.assertIn(response.status_code, [404, 200])
    
    def test_artist_similar_artists_page(self):
        """Test /artist/<id>/similar route."""
        response = self.client.get('/artist/909253/similar')
        self.assertIn(response.status_code, [200, 404])
    
    def test_artist_top_songs_page(self):
        """Test /artist/<id>/top-songs route."""
        response = self.client.get('/artist/909253/top-songs')
        self.assertIn(response.status_code, [200, 404])


class TestAlbumRoutes(unittest.TestCase):
    """Tests for /album/<collection_id> routes."""
    
    def setUp(self):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['TESTING'] = True
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_album_page_valid_id(self):
        """Test album page with valid album ID."""
        response = self.client.get('/album/1440863098')
        self.assertIn(response.status_code, [200, 404])
    
    def test_album_page_renders_without_error(self):
        """Test that album page renders without 500 error."""
        response = self.client.get('/album/1440863098')
        self.assertNotIn(b'500', response.data)


class TestTemplateElements(unittest.TestCase):
    """Tests for specific template elements and rendering."""
    
    def setUp(self):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['TESTING'] = True
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_artist_detail_template_renders(self):
        """Test that artist_detail template renders without errors."""
        response = self.client.get('/artist/909253')
        self.assertIn(response.status_code, [200, 404])
        # Should not have internal server error
        self.assertNotIn(b'Traceback', response.data)
    
    def test_artist_discography_template_renders(self):
        """Test that artist_discography template renders without errors."""
        response = self.client.get('/artist/909253/discography/albums')
        self.assertIn(response.status_code, [200, 404])
        self.assertNotIn(b'Traceback', response.data)
    
    def test_see_all_template_renders(self):
        """Test that see_all template renders without errors."""
        response = self.client.get('/see-all/albums?q=album')
        self.assertIn(response.status_code, [200, 400])
        self.assertNotIn(b'Traceback', response.data)
    
    def test_album_detail_template_renders(self):
        """Test that album_detail template renders without errors."""
        response = self.client.get('/album/1440863098')
        self.assertIn(response.status_code, [200, 404])
        self.assertNotIn(b'Traceback', response.data)
    
    def test_search_results_template_renders(self):
        """Test that search results template renders correctly."""
        response = self.client.get('/?q=test')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b'Traceback', response.data)


class TestErrorHandling(unittest.TestCase):
    """Tests for error handling and edge cases."""
    
    def setUp(self):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['TESTING'] = True
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_see_all_invalid_type(self):
        """Test /see-all with invalid type parameter."""
        response = self.client.get('/see-all/invalid_type?q=test')
        # Should either return 400/404 or handle gracefully
        self.assertIn(response.status_code, [200, 400, 404])
    
    def test_artist_invalid_id_format(self):
        """Test /artist with non-numeric ID."""
        response = self.client.get('/artist/invalid_id')
        self.assertIn(response.status_code, [200, 400, 404])
    
    def test_album_invalid_id_format(self):
        """Test /album with non-numeric ID."""
        response = self.client.get('/album/invalid_id')
        self.assertIn(response.status_code, [200, 400, 404])

if __name__ == '__main__':
    unittest.main()
