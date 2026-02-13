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
        self.assertIn(b'log in', response.data.lower())

if __name__ == '__main__':
    unittest.main()
