import unittest
from app import app, db
from models import User, Playlist, PlaylistItem, Favorite

class TestModels(unittest.TestCase):
    def setUp(self):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['TESTING'] = True
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_user_creation(self):
        user = User(username='testuser', email='test@example.com')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        
        self.assertEqual(user.username, 'testuser')
        self.assertTrue(user.check_password('password123'))
        self.assertFalse(user.check_password('wrongpassword'))

    def test_playlist_relationship(self):
        user = User(username='testuser', email='test@example.com')
        db.session.add(user)
        db.session.commit()
        
        playlist = Playlist(name='My Playlist', user_id=user.id)
        db.session.add(playlist)
        db.session.commit()
        
        item = PlaylistItem(playlist_id=playlist.id, track_id='123', title='Test Track')
        db.session.add(item)
        db.session.commit()
        
        self.assertEqual(len(user.playlists), 1)
        self.assertEqual(user.playlists[0].name, 'My Playlist')
        self.assertEqual(len(playlist.items), 1)
        self.assertEqual(playlist.items[0].title, 'Test Track')

    def test_favorite_creation(self):
        user = User(username='testuser', email='test@example.com')
        db.session.add(user)
        db.session.commit()
        
        fav = Favorite(user_id=user.id, type='artist', item_id='1', name='Artist Name')
        db.session.add(fav)
        db.session.commit()
        
        self.assertEqual(len(user.favorites), 1)
        self.assertEqual(user.favorites[0].name, 'Artist Name')

if __name__ == '__main__':
    unittest.main()
