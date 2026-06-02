"""This class is responsible for playing and pausing the music
 based on a user's mood or desire."""

import vlc  # better than pygame for streaming
import yt_dlp
import time
from ytmusicapi import YTMusic  # For accurate song search


class MusicEngine:
    def __init__(self):
        # Pygame init hata diya, VLC init laga diya
        # '--no-video' flag zaroori hai taaki video window na khule
        self.instance = vlc.Instance('--no-video')
        self.player = self.instance.media_player_new()
        self.ytmusic = YTMusic()  # API Initialize

        self._volume = 1.0
        self.is_playing = False  # Track status

    def play(self, song_name):
        """
        Searches using YTMusic API, Gets URL via yt-dlp, and Streams using VLC.
        """
        self.stop()  # Stop previous song if any

        print(f"Searching via YouTube Music: {song_name}...")

        try:
            # SEARCH: YTMusic API use kar rahe hain taaki 'Podcast' na aaye
            # filter='songs' ensures we only get music tracks
            results = self.ytmusic.search(song_name, filter="songs")

            if not results:
                print("Song not found on YouTube Music.")
                return

            # Top result details
            track = results[0]
            title = track['title']
            artist = track['artists'][0]['name'] if 'artists' in track else "Unknown"
            video_id = track['videoId']

            print(f"🎵 Found: {title} by {artist}")
            print("⚡ Fetching Stream URL (No Download)...")

            # yt-dlp se direct stream URL nikalenge
            ydl_opts = {
                'format': 'bestaudio/best',
                'quiet': True,
                'no_warnings': True,

                'extractor_args': {
                    'youtube': {
                        'player_client': ['android', 'web'],
                    }
                },
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Sirf URL nikalna hai, download=False
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
                stream_url = info['url']

            # VLC Media Player se stream karenge
            media = self.instance.media_new(stream_url)
            self.player.set_media(media)
            self.player.play()

            # Thoda wait karte hain taaki player initialize ho jaye
            time.sleep(1)

            # Volume set karte hain (VLC 0-100 leta hai, humara logic 0.0-1.0 hai)
            self.set_volume(self._volume)
            self.is_playing = True

            # DEBUG: Check player status
            print(f"VLC Status: Playing={self.player.is_playing()}")
            print(f"Now Streaming: {title}")

        except Exception as e:
            print(f"Music Error: {e}")
            import traceback
            traceback.print_exc()
            self.stop()

    def pause(self):
        if self.is_playing:
            self.player.pause()
            self.is_playing = False
            print("Music Paused")

    def resume(self):
        if not self.is_playing:
            self.player.play()  # VLC mein unpause bhi play() se hota hai agar paused hai
            self.is_playing = True
            print("Music Resumed")

    def stop(self):
        """Stops music and releases resources."""
        try:
            self.player.stop()
        except:
            pass
        self.is_playing = False
        print("Music Stopped")

    def set_volume(self, volume):
        """Set volume (0.0 to 1.0) converts to VLC (0 to 100)"""
        self._volume = max(0.0, min(1.0, volume))
        # VLC integer maangta hai (0-100)
        vlc_vol = int(self._volume * 100)
        self.player.audio_set_volume(vlc_vol)

    def check_status(self):
        # VLC returns State.Playing or State.Buffering when active
        state = self.player.get_state()
        return state in [vlc.State.Playing, vlc.State.Buffering]

    def duck_volume(self):
        """Lowers the music volume to 10%"""
        print("Ducking Volume...")
        self.set_volume(0.1)  # 10% Volume

    def restore_volume(self):
        """Restores the music volume to 100% (original)"""
        print("Restoring Volume...")
        self.set_volume(1.0)  # 100% Volume


if __name__ == "__main__":
    music = MusicEngine()
    music.play("Arjan Vailly")

    print("Code khatam hone se rok raha hu...")

    try:
        # Loop tab tak chalega jab tak gaana baj raha hai
        # Hum thoda extra check lagayenge kyunki VLC start hone me 1-2 sec leta hai
        time.sleep(2)
        while music.check_status():
            time.sleep(1)
        print("Gaana khatam, Tata Bye Bye!")

    except KeyboardInterrupt:
        music.stop()