from __future__ import annotations

from psychopy import event, visual


class InstructionScreen:
    """
    Display text instructions with an optional image on a PsychoPy window.

    Text is rendered via ``visual.TextBox2`` and images via ``visual.ImageStim``.
    When an image is provided to ``show()``, the text shifts to the top half of
    the screen and the image is placed below it.

    Parameters
    ----------
    win : visual.Window
        The PsychoPy window to draw on.
    text_color : str, optional
        Color of the instruction text. Default is 'white'.
    text_height : float | None, optional
        Height of the instruction text in normalized units. If ``None``
        (default), it is computed automatically as ~18px relative to the
        window's pixel height so the text appears the same physical size
        across different screen resolutions.
    wrap_width : float, optional
        Width of the text box before wrapping. Default is 1.4.
    continue_key : str, optional
        Key to press to advance past an instruction screen. Default is 'space'.

    Examples
    --------
    >>> from psychopy import visual
    >>> win = visual.Window(fullscr=True)
    >>> instructions = InstructionScreen(win)
    >>> instructions.show("Welcome! Press SPACE to begin.")
    >>> instructions.show("This is the target:", image='target.png')
    >>> instructions.show_pages([
    ...     "Page 1: In this task you will...",
    ...     "Page 2: When you see the target...",
    ... ])

    """

    def __init__(
        self,
        win: visual.Window,
        text_color: str = 'white',
        text_height: float | None = None,
        wrap_width: float = 1.4,
        line_spacing: float = 1.35,
        continue_key: str = 'space',
    ):
        self.win = win
        self.continue_key = continue_key

        if text_height is None:
            # ~18px in norm units: norm height = 2.0 spans win.size[1] pixels
            text_height = 16 / (win.size[1] / 2)

        self._text_stim = visual.TextBox2(
            win,
            text='',
            color=text_color,
            letterHeight=text_height,
            size=(wrap_width, None),
            pos=(0, 0),
            alignment='left',
            font='Arial',
            lineSpacing=line_spacing,
        )
        self._prompt_stim = visual.TextBox2(
            win,
            text=f'Press {continue_key.upper()} to continue',
            color='lightgray',
            letterHeight=text_height * 0.75,
            size=(wrap_width, None),
            pos=(0, -0.42),
            alignment='center',
            font='Arial',
        )

    def show(
        self,
        text: str,
        image: str | None = None,
        image_pos: tuple[float, float] = (0, -0.25),
        image_size: tuple[float, float] = (0.3, 0.3),
        continue_key: str | None = None,
    ) -> None:
        """
        Display instruction text and wait for a key press.

        Parameters
        ----------
        text : str
            The instruction text to display.
        image : str, optional
            Path to an image file to display below the text.
        image_pos : tuple, optional
            Position of the image in norm units. Default is (0, -0.25).
        image_size : tuple, optional
            Size of the image in norm units. Default is (0.3, 0.3).
        continue_key : str, optional
            Override the default continue key for this screen only.

        """
        key = continue_key or self.continue_key
        self._prompt_stim.text = f'Press {key.upper()} to continue'

        if image is not None:
            self._text_stim.pos = (0, 0.25)
            image_stim = visual.ImageStim(
                self.win,
                image=image,
                pos=image_pos,
                size=image_size,
            )
        else:
            self._text_stim.pos = (0, 0)
            image_stim = None

        self._text_stim.text = text

        event.clearEvents()
        while True:
            self._text_stim.draw()
            if image_stim is not None:
                image_stim.draw()
            self._prompt_stim.draw()
            self.win.flip()

            keys = event.getKeys(keyList=[key, 'escape'])
            if 'escape' in keys:
                self.win.close()
                return
            if key in keys:
                return

    def show_pages(
        self,
        pages: list[str | dict],
        continue_key: str | None = None,
    ) -> None:
        """
        Display multiple pages of instructions in sequence.

        Each page can be a plain string or a dict with the following keys:

        - ``text`` (str): The instruction text.
        - ``image`` (str, optional): Path to an image file.
        - ``image_pos`` (list, optional): Image position in norm units.
        - ``image_size`` (list, optional): Image size in norm units.

        Parameters
        ----------
        pages : list[str | dict]
            List of instruction pages.
        continue_key : str, optional
            Override the default continue key for all pages.

        """
        for page in pages:
            if isinstance(page, dict):
                self.show(
                    page['text'],
                    image=page.get('image'),
                    image_pos=tuple(page['image_pos']) if 'image_pos' in page else (0, -0.25),
                    image_size=tuple(page['image_size']) if 'image_size' in page else (0.3, 0.3),
                    continue_key=continue_key,
                )
            else:
                self.show(page, continue_key=continue_key)
