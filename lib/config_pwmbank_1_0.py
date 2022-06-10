# overwrite wrong PCB routing. Make ML10_PMW1 light up the first output

if 0 == 1:
    # make pylint think that it knows about 'const' variable
    const = lambda x: x


def patch_ml10_1(board):
    board.ML10_PWM_1 = 19
    board.ML10_PWM_2 = 5
    board.ML10_PWM_3 = 16
    board.ML10_PWM_4 = 15
    board.ML10_PWM_5 = 4
    board.ML10_PWM_6 = 17
    board.ML10_PWM_7 = 18
    board.ML10_PWM_8 = 21

# def init():
#     """dummy"""
#     print('1: {}, 2: {}'.format(bconf.ML10_PWM_1, bconf.ML10_PWM_2))

