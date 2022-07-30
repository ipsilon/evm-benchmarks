
EVMMAX_ARITH_ITER_COUNT = 1

MAX_LIMBS = 11

EVMMAX_ARITH_OPS = {
    "SETMODMAX": "0c",
    "ADDMODMAX": "0d",
    "SUBMODMAX": "0e",
    "MULMONTMAX": "0f",
}

LIMB_SIZE = 8

SETMOD_OP = "0c"

EVMMAX_ARITH_OPS = {
    "ADDMODMAX": "0d",
    "SUBMODMAX": "0e",
    "MULMONTMAX": "0f",
}

EVM_OPS = {
    "MSTORE": "52" # TODO
}

def pad_be_limb(word: str):
    assert len(word) <= LIMB_SIZE * 2, "invalid length"
    
    if len(word) < LIMB_SIZE * 2:
        return '0'*(LIMB_SIZE * 2 - len(word)) + word
    else:
        return word

def reverse_endianess(word: str):
    assert len(word) == LIMB_SIZE * 2, "invalid length"

    result = ""
    for i in reversed(range(0, len(word), 2)):
        result += word[i:i+2]
    return result

def calc_limb_count(val: int) -> int:
    assert val > 0, "val must be greater than 0"

    count = 0
    while val != 0:
        val >>= 64
        count += 1
    return count

# convert an int a little-endian list of 64bit-value limbs
def int_to_be_limbs(val: int, limb_count: int) -> [int]:
    if val == 0:
        return ['00'] * limb_count

    result = []
    while val != 0:
        limb = val % (1 << 64)
        val >>= 64
        result.append(hex(limb)[2:])

    if len(result) < limb_count:
        result = [0] * (limb_count - len(result)) + result

    return [pad_be_limb(limb) for limb in reversed(result)]

def gen_push_int(val: int) -> str:
    assert val >= 0 and val < (1 << 256), "val must be in acceptable evm word range"

    literal = hex(val)[2:]
    if len(literal) % 2 == 1:
        literal = "0" + literal
    return gen_push_literal(literal)

def gen_push_literal(val: str) -> str:
    assert len(val) <= 64, "val is too big"
    assert len(val) % 2 == 0, "val must be even length"
    push_start = 0x60
    push_op = hex(push_start - 1 + int(len(val) / 2))[2:]

    assert len(push_op) == 2, "bug"

    return push_op + val

def gen_mstore_int(val: int, offset: int) -> str:
    return gen_push_int(val) + gen_push_int(offset) + EVM_OPS["MSTORE"]

def gen_mstore_literal(val: str, offset: int) -> str:
    return gen_push_literal(val) + gen_push_int(offset) + EVM_OPS["MSTORE"]

def gen_mstore_evmmax_elem(dst_slot: int, val: int, limb_count: int) -> str:
    assert dst_slot >= 0 and dst_slot < 11, "invalid dst_slot"

    limbs = int_to_be_limbs(val, limb_count)
    evm_word = ""
    result = ""
    offset = dst_slot * limb_count * LIMB_SIZE
    for i in range(len(limbs)):
        if i != 0 and i % 4 == 0:
            result += gen_mstore_literal(evm_word, offset)
            evm_word = limbs[i]
            offset += 32
        else:
            evm_word += limbs[i]
    result += gen_mstore_literal(evm_word, offset)
    return result

def gen_encode_evmmax_bytes(*args):
    result = ""
    for b1 in args:
        assert b1 >= 0 and b1 < 256, "argument must be in byte range"

        b1 = hex(b1)[2:]
        if len(b1) == 1:
            b1 = '0'+b1

        result += b1
    return result

def gen_setmod(slot: int, mod: int) -> str:
    limb_count = calc_limb_count(mod)
    result = gen_mstore_evmmax_elem(slot, mod, limb_count)
    result += gen_push_literal(gen_encode_evmmax_bytes(0, limb_count))
    result += SETMOD_OP
    return result

# return largest-possible mod representable with a given limb count
def gen_mod(limb_count: int) -> int:
    return (1 << (limb_count * LIMB_SIZE * 8)) - 1

def gen_evmmax_worst_input(op: str, limb_count: int) -> (int, int):
    return 0, 0

def gen_evmmax_op(op: str, out_slot: int, x_slot: int, y_slot: int) -> str:
    return gen_push_literal(gen_encode_evmmax_bytes(out_slot, x_slot, y_slot)) + EVMMAX_ARITH_OPS[op]

def gen_arith_loop_benchmark(op: str, limb_count: str) -> str:
    mod = gen_mod(limb_count)
    setmod = gen_setmod(0, mod)

    end_mem = limb_count * 8 * 4 # the offset of the first word beyond the end of the last slot we will use
    expand_memory = gen_mstore_int(end_mem, 0)

    x_input, y_input = gen_evmmax_worst_input(op, limb_count)
    store_inputs = gen_mstore_evmmax_elem(1, x_input, limb_count) + gen_mstore_evmmax_elem(2, y_input, limb_count)
    
    bench_start = expand_memory + setmod + store_inputs 
    loop_body = ""

    for i in range(EVMMAX_ARITH_ITER_COUNT):
        loop_body += gen_evmmax_op(op, 0, 1, 2)

    return gen_loop().format(bench_start, loop_body)

def gen_loop() -> str:
    return "{}7fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff01{}60010180602157"

res = gen_arith_loop_benchmark("MULMONTMAX", 5)
import pdb; pdb.set_trace()
