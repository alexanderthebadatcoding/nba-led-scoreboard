from PIL import Image, ImageFont, ImageDraw, ImageSequence
from rgbmatrix import graphics
from utils import center_text
from calendar import month_abbr
from renderer.screen_config import screenConfig
from datetime import datetime, timedelta
import time as t
import debug
import re

GAMES_REFRESH_RATE = 900.0

class MainRenderer:
    def __init__(self, matrix, data):
        self.matrix = matrix
        self.data = data
        self.screen_config = screenConfig("64x32_config")
        self.canvas = matrix.CreateFrameCanvas()
        self.width = 64
        self.height = 32
        # Create a new data image.
        self.image = Image.new('RGB', (self.width, self.height))
        self.draw = ImageDraw.Draw(self.image)
        # Load the fonts
        self.font = ImageFont.truetype("fonts/score_large.otf", 16)
        self.font_mini = ImageFont.truetype("fonts/04B_24__.TTF", 8)

    def render(self):
        while True:
            self.starttime = t.time()
            self.data.get_current_date()
            self.__render_game()

    def __render_game(self):
        while True:
            # If we need to refresh the overview data, do that
            if self.data.needs_refresh:
                self.data.refresh_games()

            # Draw the current game
            self.__draw_game(self.data.current_game())

            # Set the refresh rate
            refresh_rate = self.data.config.scrolling_speed
            t.sleep(refresh_rate)
            endtime = t.time()
            time_delta = endtime - self.starttime
            rotate_rate = self.__rotate_rate_for_game(self.data.current_game())

            # If we're ready to rotate, let's do it
            # fix this u idiot
            if time_delta >= rotate_rate:
                self.starttime = t.time()
                self.data.needs_refresh = True

                if self.__should_rotate_to_next_game(self.data.current_game()):
                    game = self.data.advance_to_next_game()

                if endtime - self.data.games_refresh_time >= GAMES_REFRESH_RATE:
                    self.data.refresh_games()

                if self.data.needs_refresh:
                    self.data.refresh_games()

    def __rotate_rate_for_game(self, game):
        rotate_rate = self.data.config.rotation_rates_live
        if game['state'] == 'pre':
            rotate_rate = self.data.config.rotation_rates_pregame
        if game['state'] == 'post':
            rotate_rate = self.data.config.rotation_rates_final
        return rotate_rate

    def __should_rotate_to_next_game(self, game):
        if self.data.config.rotation_enabled == False:
            return False

        stay_on_preferred_team = self.data.config.preferred_teams and not self.data.config.rotation_preferred_team_live_enabled
        if stay_on_preferred_team == False:
            return True
        else:
            return False

    def __draw_game(self, game):
        time = self.data.get_current_date()
        gametime = datetime.strptime(game['date'], "%Y-%m-%dT%H:%MZ")
        if time < gametime - timedelta(hours=1) and game['state'] == 'pre':
            debug.info('Pre-Game State')
            self._draw_pregame(game)
        elif time < gametime and game['state'] == 'pre':
            debug.info('Countdown til gametime')
            self._draw_countdown(game)
        elif game['state'] == 'post':
            debug.info('Final State')
            self._draw_post_game(game)
        else:
            debug.info('Live State, checking every 5s')
            self._draw_live_game(game)
        debug.info('ping render_game')

    def _draw_pregame(self, game):
            time = self.data.get_current_date()
            gamedatetime = self.data.get_gametime()
            if gamedatetime.day == time.day:
                date_text = 'TODAY'
            else:
                date_text = gamedatetime.strftime('%A %-d %b').upper()
            gametime = gamedatetime.strftime("%-I:%M %p")
            # Center the game time on screen.                
            date_pos = center_text(self.font_mini.getsize(date_text)[0], 32)
            gametime_pos = center_text(self.font_mini.getsize(gametime)[0], 32)
            # Draw the text on the Data image.
            self.draw.text((date_pos, 0), date_text, font=self.font_mini)
            self.draw.multiline_text((gametime_pos, 6), gametime, fill=(255, 255, 255), font=self.font_mini, align="center")
            self.draw.text((25, 15), 'VS', font=self.font)
            # Put the data on the canvas
            self.canvas.SetImage(self.image, 0, 0)
            if self.data.nba_logos:
                # Open the logo image file
                away_team_logo = Image.open('logos/{}H.png'.format(game['awayteam'])).resize((20, 20), 1)
                home_team_logo = Image.open('logos/{}H.png'.format(game['hometeam'])).resize((20, 20), 1)
                # Put the images on the canvas
                self.canvas.SetImage(away_team_logo.convert("RGB"), 1, 12)
                self.canvas.SetImage(home_team_logo.convert("RGB"), 43, 12)
            else:
                # TEMP Open the logo image file
                away_team_logo = Image.open('logos/{}.png'.format(game['awayteam'])).resize((20, 20), Image.BOX)
                home_team_logo = Image.open('logos/{}.png'.format(game['hometeam'])).resize((20, 20), Image.BOX)
                # Put the images on the canvas
                self.canvas.SetImage(away_team_logo.convert("RGB"), 1, 12)
                self.canvas.SetImage(home_team_logo.convert("RGB"), 43, 12)

            # Load the canvas on screen.
            self.canvas = self.matrix.SwapOnVSync(self.canvas)
            # Refresh the Data image.
            self.image = Image.new('RGB', (self.width, self.height))
            self.draw = ImageDraw.Draw(self.image)

    def _draw_countdown(self, game):
        time = self.data.get_current_date()
        gametime = datetime.strptime(game['date'], "%Y-%m-%dT%H:%MZ")
        if time < gametime:
            gt = gametime - time
            # as beautiful as I am
            if gt > timedelta(hours=1):
                gametime = ':'.join(str(gametime - time).split(':')[:2])
            else:
                gametime = ':'.join(str(gametime - time).split(':')[1:]).split('.')[:1][0]
            # Center the game time on screen.
            gametime_pos = center_text(self.font_mini.getsize(gametime)[0], 32)
            # Draw the text on the Data image.
            self.draw.text((29, 0), 'IN', font=self.font_mini)
            self.draw.multiline_text((gametime_pos, 6), gametime, fill=(255, 255, 255), font=self.font_mini, align="center")
            self.draw.text((25, 15), 'VS', font=self.font)
            # Put the data on the canvas
            self.canvas.SetImage(self.image, 0, 0)
            if self.data.nba_logos:
                # Open the logo image file
                away_team_logo = Image.open('logos/{}H.png'.format(game['awayteam'])).resize((20, 20), 1)
                home_team_logo = Image.open('logos/{}H.png'.format(game['hometeam'])).resize((20, 20), 1)
                # Put the images on the canvas
                self.canvas.SetImage(away_team_logo.convert("RGB"), 1, 12)
                self.canvas.SetImage(home_team_logo.convert("RGB"), 43, 12)
            else:
                # TEMP Open the logo image file
                away_team_logo = Image.open('logos/{}.png'.format(game['awayteam'])).resize((20, 20), Image.BOX)
                home_team_logo = Image.open('logos/{}.png'.format(game['hometeam'])).resize((20, 20), Image.BOX)
                # Put the images on the canvas
                self.canvas.SetImage(away_team_logo.convert("RGB"), 1, 12)
                self.canvas.SetImage(home_team_logo.convert("RGB"), 43, 12)
            # Load the canvas on screen.
            self.canvas = self.matrix.SwapOnVSync(self.canvas)
            # Refresh the Data image.
            self.image = Image.new('RGB', (self.width, self.height))
            self.draw = ImageDraw.Draw(self.image)
            # t.sleep(1)

    def _draw_live_game(self, game):
        homescore = game['homescore']
        awayscore = game['awayscore']
        print("home: ", homescore, "away: ", awayscore)
        # Refresh the data
        if self.data.needs_refresh:
            debug.info('Refresh game overview')
            self.data.refresh_games()
            self.data.needs_refresh = False
        quarter = str(game['quarter'])
        time_period = game['time']
        
        # Set the position of the information on screen.
        homescore = '{0:02d}'.format(homescore)
        awayscore = '{0:02d}'.format(awayscore)
        home_score_size = self.font.getsize(homescore)[0]
        home_score_pos = center_text(self.font.getsize(homescore)[0], 16)
        away_score_pos = center_text(self.font.getsize(awayscore)[0], 48)
        time_period_pos = center_text(self.font_mini.getsize(time_period)[0], 32)
        # score_position = center_text(self.font.getsize(score)[0], 32)
        quarter_position = center_text(self.font_mini.getsize(quarter)[0], 32)
        # info_pos = center_text(self.font_mini.getsize(pos)[0], 32)
        # self.draw.multiline_text((info_pos, 13), pos, fill=pos_colour, font=self.font_mini, align="center")
        self.draw.multiline_text((quarter_position, 0), quarter, fill=(255, 255, 255), font=self.font_mini, align="center")
        self.draw.multiline_text((time_period_pos, 6), time_period, fill=(255, 255, 255), font=self.font_mini, align="center")
        self.draw.multiline_text((6, 19), awayscore, fill=(255, 255, 255), font=self.font, align="center")
        self.draw.multiline_text((59 - home_score_size, 19), homescore, fill=(255, 255, 255), font=self.font, align="center")
        # Put the data on the canvas
        self.canvas.SetImage(self.image, 0, 0)
        if self.data.nba_logos:
            # Open the logo image file
            away_team_logo = Image.open('logos/{}H.png'.format(game['awayteam'])).resize((20, 20), 1)
            home_team_logo = Image.open('logos/{}H.png'.format(game['hometeam'])).resize((20, 20), 1)
            # Put the images on the canvas
            self.canvas.SetImage(away_team_logo.convert("RGB"), 1, 0)
            self.canvas.SetImage(home_team_logo.convert("RGB"), 43, 0)
        else:
            # TEMP Open the logo image file
            away_team_logo = Image.open('logos/{}.png'.format(game['awayteam'])).resize((20, 20), Image.BOX)
            home_team_logo = Image.open('logos/{}.png'.format(game['hometeam'])).resize((20, 20), Image.BOX)
            # Put the images on the canvas
            self.canvas.SetImage(away_team_logo.convert("RGB"), 1, 0)
            self.canvas.SetImage(home_team_logo.convert("RGB"), 43, 0)
        # Set the position of each logo on screen.
        # Load the canvas on screen.
        self.canvas = self.matrix.SwapOnVSync(self.canvas)
        # Refresh the Data image.
        self.image = Image.new('RGB', (self.width, self.height))
        self.draw = ImageDraw.Draw(self.image)
        # Check if the game is over
        if game['state'] == 'post':
            debug.info('GAME OVER')
        # Save the scores.
        # awayscore = game['awayscore']
        # homescore = game['homescore']
        self.data.needs_refresh = True

    def _draw_post_game(self, game):
        # Prepare the data
        score = '{}-{}'.format(game['awayscore'], game['homescore'])
        # Set the position of the information on screen.
        score_position = center_text(self.font.getsize(score)[0], 32)
        # Draw the text on the Data image.
        self.draw.multiline_text((score_position, 19), score, fill=(255, 255, 255), font=self.font, align="center")
        self.draw.multiline_text((26, 0), "END", fill=(255, 255, 255), font=self.font_mini,align="center")
        # Put the data on the canvas
        self.canvas.SetImage(self.image, 0, 0)
        if self.data.nba_logos:
            # Open the logo image file
            away_team_logo = Image.open('logos/{}H.png'.format(game['awayteam'])).resize((20, 20), 1)
            home_team_logo = Image.open('logos/{}H.png'.format(game['hometeam'])).resize((20, 20), 1)
            # Put the images on the canvas
            self.canvas.SetImage(away_team_logo.convert("RGB"), 1, 0)
            self.canvas.SetImage(home_team_logo.convert("RGB"), 43, 0)
        else:
            # TEMP Open the logo image file
            away_team_logo = Image.open('logos/{}.png'.format(game['awayteam'])).resize((20, 20), Image.BOX)
            home_team_logo = Image.open('logos/{}.png'.format(game['hometeam'])).resize((20, 20), Image.BOX)
            # Put the images on the canvas
            self.canvas.SetImage(away_team_logo.convert("RGB"), 1, 0)
            self.canvas.SetImage(home_team_logo.convert("RGB"), 43, 0)
        # Load the canvas on screen.
        self.canvas = self.matrix.SwapOnVSync(self.canvas)
        # Refresh the Data image.
        self.image = Image.new('RGB', (self.width, self.height))
        self.draw = ImageDraw.Draw(self.image)