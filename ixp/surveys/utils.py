from __future__ import annotations

from psychopy import visual


def build_ui(win, questions):
    n_questions = len(questions)

    # 1. Define vertical boundaries
    top_limit = 0.45
    bottom_limit = -0.40
    available_height = top_limit - bottom_limit

    # 2. Divide screen into rows based on question count
    row_height = available_height / n_questions

    # 3. Visual Constants
    # We keep text_height and slider_thickness consistent,
    # but they can be slightly scaled if n_questions is very high.
    text_height = 0.022 if n_questions > 6 else 0.024
    slider_thickness = 0.03

    # This is your fixed gap between the text and the slider
    # By making this a constant, the spacing remains identical
    # across different question counts.
    fixed_gap = 0.05

    texts = []
    sliders = []
    for idx, (label, question, lo, hi) in enumerate(questions):
        # Calculate the top boundary of this specific question row
        row_top = top_limit - (idx * row_height)

        # Position Text:
        # Anchored at the very top of its row segment
        title = visual.TextStim(
            win,
            text=f'{label}: {question}',
            pos=(0, row_top),
            height=text_height,
            wrapWidth=1.2,
            color='white',
            alignText='center',
            anchorVert='top',  # Grows downward from row_top
            font='Arial',
        )

        # Position Slider:
        # Instead of placing it at the bottom of the row,
        # we place it at exactly (row_top - fixed_gap).
        slider = visual.Slider(
            win,
            ticks=(1, 100),
            labels=[lo, hi],
            pos=(0, row_top - fixed_gap),
            size=(1.0, slider_thickness),
            granularity=1,
            style=['rating'],
            color='white',
            labelHeight=text_height * 0.8,
            font='Arial',
        )
        slider.markerPos = 50

        texts.append(title)
        sliders.append(slider)

    # Confirm Instruction
    instruction = visual.TextStim(
        win,
        text='Adjust all sliders and press SPACE to confirm',
        pos=(0, -0.47),
        height=0.018,
        color='lightgray',
    )

    return texts, sliders, instruction
