import tempfile
import os
from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor

MOVIE_URL = reverse("cinema:movie-list")

def sample_movie(**params):
    defaults = {"title": "Sample", "description": "Desc", "duration": 90}
    defaults.update(params)
    return Movie.objects.create(**defaults)

def sample_genre(**params):
    defaults = {"name": "Drama"}
    defaults.update(params)
    return Genre.objects.create(**defaults)

def sample_actor(**params):
    defaults = {"first_name": "John", "last_name": "Doe"}
    defaults.update(params)
    return Actor.objects.create(**defaults)

class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user("test@test.com", "pass12345")
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        sample_movie()
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_filter_movies_by_title(self):
        m1 = sample_movie(title="Inception")
        m2 = sample_movie(title="Avatar")
        res = self.client.get(MOVIE_URL, {"title": "Incep"})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], m1.title)

    def test_filter_movies_by_genres(self):
        g1 = sample_genre(name="Action")
        m1 = sample_movie(title="M1")
        m1.genres.add(g1)
        res = self.client.get(MOVIE_URL, {"genres": f"{g1.id}"})
        self.assertEqual(len(res.data), 1)

    def test_filter_movies_by_actors(self):
        a1 = sample_actor()
        m1 = sample_movie(title="M1")
        m1.actors.add(a1)
        res = self.client.get(MOVIE_URL, {"actors": f"{a1.id}"})
        self.assertEqual(len(res.data), 1)

    def test_create_movie_forbidden(self):
        payload = {"title": "Forbidden", "description": "Desc", "duration": 100}
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

class AdminMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser("admin@test.com", "pass12345")
        self.client.force_authenticate(self.user)
        self.movie = sample_movie()

    def test_upload_image_to_movie(self):
        url = reverse("cinema:movie-upload-image", args=[self.movie.id])
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")
        self.movie.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(os.path.exists(self.movie.image.path))
        self.movie.image.delete()