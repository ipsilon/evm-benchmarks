
MAX_LIMBS = 11

EVMMAX_ARITH_OPS = {
    "SETMODMAX": "0c",
    "ADDMODMAX": "0d",
    "SUBMODMAX": "0e",
    "MULMONTMAX": "0f",
}

LIMB_SIZE = 8

EVMMAX_ARITH_OPS = {
    "SETMODMAX": "0c",
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

# convert an int a little-endian list of 64bit-value limbs
def int_to_be_limbs(val: int, limb_count: int) -> [int]:
    if val == 0:
        return [0] * limb_count

    result = []
    while val != 0:
        limb = val % (1 << 64)
        val >>= 64
        result.append(hex(limb)[2:])

    if len(result) < limb_count:
        result = [0] * (limb_count - len(result)) + result

    return [pad_be_limb(limb) for limb in reversed(result)]

def gen_push_int(val: int) -> str:
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

def gen_mstore_literal(val: str, offset: int) -> str:
    return gen_push_literal(val) + gen_push_int(offset) + EVM_OPS["MSTORE"]

def gen_mstore_evmmax_elem(dst_slot: int, val: int, limb_count: int) -> str:
    assert dst_slot >= 0 and dst_slot < 11, "invalid dst_slot"

    limbs = int_to_be_limbs(val, limb_count)
    evm_word = ""
    result = ""
    offset = dst_slot * limb_count * LIMB_SIZE
    for i in range(len(limbs)):
        evm_word += limbs[i]
        if i != 0 and i % 4 == 0:
            result += gen_mstore_literal(evm_word, offset)
            evm_word = ""
            offset += 32
    result += gen_mstore_literal(evm_word, offset)
    return result

def gen_arith_loop_benchmark(op: str, limb_count: str) -> str:
    mod = gen_mod(limb_count)
    setmod = gen_setmod(mod, 0)

    end_mem = limb_count * 8 * 4 # the offset of the first word beyond the end of the last slot we will use
    expandmemory = gen_push_int(end_mem) + gen_push_word(0) + gen_mstore()

    x_input, y_input = gen_evmmax_worst_input(op, limb_count)
    store_inputs = gen_mstore_evmmax_input(1, x_input) + gen_mstore_evmmax_input(2, y_input)
    
    bench_start = setmod + expand_memory + store_inputs 
    loop_body = ""

    for i in range(EVMMAX_ARITH_ITER_COUNT):
        loop_body += gen_evmmax_op(op, 0, 1, 2)

    return gen_loop().format(bench_start, loop_body)

def gen_loop() -> str:
    return "{}7fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff01{}60010180602157"
import pdb; pdb.set_trace()
