from abc import ABC, abstractmethod


class Player(ABC):
    """Abstract Player which contains core methods."""

    @property
    @abstractmethod
    def state(self):
        """
        STATES:
            0  = Stopped/No file
            1  = Paused
            2  = Playing
        """
        pass

    @property
    @abstractmethod
    def position(self):
        """The seconds elapsed since beginning of file."""
        pass

    @property
    @abstractmethod
    def duration(self):
        """The total duration of file in seconds."""
        pass

    @property
    @abstractmethod
    def file_path(self):
        """Full path of the currently playing media."""
        pass

    @abstractmethod
    def check_running(self):
        """Determine whether or not the player is running."""
        pass

    @abstractmethod
    def update_status(self):
        """Query the player for its current status."""
        pass
