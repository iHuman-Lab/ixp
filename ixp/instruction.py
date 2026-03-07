from __future__ import annotations

from psychopy import event, visual


class InstructionScreen:
    """
    Display text instructions on a PsychoPy window.

    Parameters
    ----------
    win : visual.Window
        The PsychoPy window to draw on.
    text_color : str, optional
        Color of the instruction text. Default is 'white'.
    text_height : float, optional
        Height of the instruction text in normalized units. Default is 0.05.
    wrap_width : float, optional
        Maximum line width before wrapping. Default is 1.4.
    continue_key : str, optional
        Key to press to advance past an instruction screen. Default is 'space'.

    Examples
    --------
    >>> from psychopy import visual
    >>> win = visual.Window(fullscr=True)
    >>> instructions = InstructionScreen(win)
    >>> instructions.show("Welcome! Press SPACE to begin.")
    >>> instructions.show_pages([
    ...     "Page 1: In this task you will...",
    ...     "Page 2: When you see the target...",
    ... ])

    """

    def __init__(
        self,
        win: visual.Window,
        text_color: str = 'white',
        text_height: float = 0.05,
        wrap_width: float = 1.4,
        continue_key: str = 'space',
    ):
        self.win = win
        self.continue_key = continue_key

        self._text_stim = visual.TextStim(
            win,
            text='',
            color=text_color,
            height=text_height,
            wrapWidth=wrap_width,
            alignText='center',
            anchorVert='center',
            font='Arial',
        )
        self._prompt_stim = visual.TextStim(
            win,
            text=f'Press {continue_key.upper()} to continue',
            color='lightgray',
            height=text_height * 0.6,
            pos=(0, -0.42),
            font='Arial',
        )

    def show(self, text: str, continue_key: str | None = None) -> None:
        """
        Display instruction text and wait for a key press.

        Parameters
        ----------
        text : str
            The instruction text to display.
        continue_key : str, optional
            Override the default continue key for this screen only.

        """
        key = continue_key or self.continue_key
        self._prompt_stim.text = f'Press {key.upper()} to continue'
        self._text_stim.text = text

        event.clearEvents()
        while True:
            self._text_stim.draw()
            self._prompt_stim.draw()
            self.win.flip()

            keys = event.getKeys(keyList=[key, 'escape'])
            if 'escape' in keys:
                self.win.close()
                return
            if key in keys:
                return

    def show_pages(self, pages: list[str], continue_key: str | None = None) -> None:
        """
        Display multiple pages of instructions in sequence.

        Parameters
        ----------
        pages : list[str]
            List of instruction strings, one per page.
        continue_key : str, optional
            Override the default continue key for all pages.

        """
        for page in pages:
            self.show(page, continue_key)
