from unittest.mock import Mock

import pytest

from src.utils.spotify_compat import create_playlist


@pytest.mark.parametrize(
    ('name', 'description', 'message'),
    [
        ('', '', 'necesita un nombre'),
        ('x' * 101, '', 'no puede superar 100'),
        ('Nombre', 'x' * 301, 'no puede superar 300'),
    ],
)
def test_create_playlist_validates_spotify_limits(name, description, message):
    spotify = Mock()

    with pytest.raises(ValueError, match=message):
        create_playlist(spotify, name, description=description)

    spotify._post.assert_not_called()
