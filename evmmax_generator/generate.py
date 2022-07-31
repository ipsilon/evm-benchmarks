import math

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
        limb_hex = hex(limb)[2:]
        if len(limb_hex) < LIMB_SIZE * 2:
            limb_hex = ((LIMB_SIZE * 2) - len(limb_hex)) * '0' + limb_hex
        result.append(limb_hex)

    if len(result) < limb_count:
        result = result + ['0'] * (limb_count - len(result))

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
            evm_word = limbs[len(limbs) - i - 1]
            offset += 32
        else:
            evm_word += limbs[len(limbs) - i - 1]

    if len(evm_word) < 64:
        evm_word = evm_word + "0" * (64 - len(evm_word))
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
    result += gen_push_literal(gen_encode_evmmax_bytes(limb_count, slot))
    result += SETMOD_OP
    return result

# return modulus roughly in the middle of the range that can be represented with limb_count
def gen_mod(limb_count: int) -> int:
    mod = (1 << ((limb_count - 1) * LIMB_SIZE * 8) + int((LIMB_SIZE * 8) / 2)) - 1
    return mod

def worst_case_mulmontmax_input(limb_count: int) -> int:
    mod = gen_mod(limb_count)
    r = 1 << (limb_count * LIMB_SIZE * 8)
    r_inv = pow(-mod, -1, r)
    
    # res = math.ceil(math.sqrt((mod * r) / (mod * r_inv + 1))) 
    return mod - 1#res

# generate the slowest inputs for the maximum modulus representable by limb_count limbs
def gen_evmmax_worst_input(op: str, limb_count: int) -> (int, int):
    if op == "MULMONTMAX":
        # TODO generate inputs to make the final subtraction happen
        # want ((x * y * n_inv) * mod + x * y) / R < N
        val = worst_case_mulmontmax_input(limb_count)
        # TODO yoloing here
        return val, val>>16
    elif op == "ADDMODMAX":
        pass
    elif op == "SUBMODMAX":
        pass
    else:
        raise Exception("unknown evmmax arith op")

def gen_evmmax_op(op: str, out_slot: int, x_slot: int, y_slot: int) -> str:
    return gen_push_literal(gen_encode_evmmax_bytes(out_slot, x_slot, y_slot)) + EVMMAX_ARITH_OPS[op]

MAX_CONTRACT_SIZE = 24576

def gen_arith_loop_benchmark(op: str, limb_count: str) -> str:
    mod = gen_mod(limb_count)
    setmod = gen_setmod(0, mod)

    end_mem = limb_count * 8 * 4 # the offset of the first word beyond the end of the last slot we will use
    expand_memory = gen_mstore_int(end_mem, 0)

    x_input, y_input = gen_evmmax_worst_input(op, limb_count)
    #import pdb; pdb.set_trace()
    store_inputs = gen_mstore_evmmax_elem(1, x_input, limb_count) + gen_mstore_evmmax_elem(2, y_input, limb_count)
    
    bench_start = expand_memory + setmod + store_inputs 
    loop_body = ""

    empty_bench_len = int(len(gen_loop().format(bench_start, "", gen_push_int(258))) / 2)
    free_size = MAX_CONTRACT_SIZE - empty_bench_len
    iter_size = 5 # PUSH3 + 3byte immediate + EVMMAX_ARITH_OPCODE
    iter_count = math.floor(free_size / 5)
    for i in range(iter_count):
        loop_body += gen_evmmax_op(op, 0, 1, 2)

    # TODO don't hardcode jumpdest pc (258)
    res = gen_loop().format(bench_start, loop_body, gen_push_int(258))
    assert len(res) / 2 <= MAX_CONTRACT_SIZE, "benchmark greater than max contract size"
    return res

def gen_loop() -> str:
    return "{}7fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff015b{}60010180{}57"

print("0x"+gen_arith_loop_benchmark("MULMONTMAX", 5))
