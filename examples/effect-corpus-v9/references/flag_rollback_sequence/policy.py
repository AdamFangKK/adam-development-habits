def evaluate(flag_exists):
    return ('disable_flag', 'revert_code') if flag_exists else ('revert_code',)
