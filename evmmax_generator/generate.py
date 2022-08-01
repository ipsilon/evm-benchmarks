import math
import os
import sys
import subprocess

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

# split a value into 256bit big-endian words, return them in little-endian format
def int_to_evm_words(val: int, evm384_limb_count: int) -> [str]:
    result = []
    if val == 0:
        return ['00']

    og_val = val
    while val != 0:
        limb = val % (1 << 256)
        val >>= 256

        if limb == 0:
            result.append("00")
            continue

        limb_hex = hex(limb)[2:]
        if len(limb_hex) % 2 != 0:
            limb_hex = "0" + limb_hex

        limb_hex = reverse_endianess(limb_hex)
        if len(limb_hex) < 64:
            limb_hex += (64 - len(limb_hex)) * "0"

        result.append(limb_hex)

    if len(result) * 32 < evm384_limb_count * LIMB_SIZE:
        result = ['00'] * math.ceil((limb_count * LIMB_SIZE - len(result) * 32) / 32) + result

    return list(reversed(result))

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

def reverse_endianess(val: str):
    assert len(val) % 2 == 0, "must have even string"
    result = ""
    for i in reversed(range(0, len(val), 2)):
        result += val[i:i+2]

    return result

def gen_mstore_evmmax_elem(dst_slot: int, val: int, limb_count: int) -> str:
    assert dst_slot >= 0 and dst_slot < 11, "invalid dst_slot"

    evm_words = int_to_evm_words(val, limb_count)
    result = ""
    offset = dst_slot * limb_count * LIMB_SIZE
    for word in evm_words:
        result += gen_mstore_literal(word, offset)
        offset += 32

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
    mod = (1 << ((limb_count - 1) * LIMB_SIZE * 8 + 8)) - 1
    return mod

def worst_case_mulmontmax_input(limb_count: int) -> (int, int):
    mod = gen_mod(limb_count)
    r = 1 << (limb_count * LIMB_SIZE * 8)
    r_inv = pow(-mod, -1, r)
    
    # TODO figure this out

    # choose x == y: (x**2 * n_inv * mod + x ** 2) / R < N
    #return res
    # import pdb; pdb.set_trace()
    return mod - 1, mod - 1

def worst_case_addmodmax_inputs(limb_count: int) -> (int, int):
    mod = gen_mod(limb_count)
    x = mod - 2

    return x, 1

def worst_case_submodmax_inputs(limb_count: int) -> (int, int):
    return 1, 0

# generate the slowest inputs for the maximum modulus representable by limb_count limbs
def gen_evmmax_worst_input(op: str, limb_count: int) -> (int, int):
    if op == "MULMONTMAX":
        # TODO generate inputs to make the final subtraction happen
        return worst_case_mulmontmax_input(limb_count)
    elif op == "ADDMODMAX":
        return worst_case_addmodmax_inputs(limb_count)
    elif op == "SUBMODMAX":
        return worst_case_submodmax_inputs(limb_count)
    else:
        raise Exception("unknown evmmax arith op")

def gen_evmmax_op(op: str, out_slot: int, x_slot: int, y_slot: int) -> str:
    return gen_push_literal(gen_encode_evmmax_bytes(out_slot, x_slot, y_slot)) + EVMMAX_ARITH_OPS[op]

MAX_CONTRACT_SIZE = 24576

def gen_arith_loop_benchmark(op: str, limb_count: str) -> str:
    mod = gen_mod(limb_count)
    setmod = gen_setmod(0, mod)

    # mod_mem = limb_count * 8 * 4 # the offset of the first word beyond the end of the last slot we will use
    # expand_memory = gen_mstore_int(end_mem, 0)

    x_input, y_input = gen_evmmax_worst_input(op, limb_count)
    store_inputs = gen_mstore_evmmax_elem(1, x_input, limb_count) + gen_mstore_evmmax_elem(2, y_input, limb_count)
    
    bench_start = setmod + store_inputs 
    loop_body = ""

    empty_bench_len = int(len(gen_loop().format(bench_start, "", gen_push_int(258))) / 2)
    free_size = MAX_CONTRACT_SIZE - empty_bench_len
    iter_size = 5 # PUSH3 + 3byte immediate + EVMMAX_ARITH_OPCODE
    iter_count = math.floor(free_size / 5)

    inner_loop_evmmax_op_count = 0

    for i in range(iter_count):
        loop_body += gen_evmmax_op(op, 0, 1, 2)
        inner_loop_evmmax_op_count += 1

    loop_iterations = 256 # TODO verify this
    inner_loop_evmmax_op_count *= loop_iterations

    res = gen_loop().format(bench_start, loop_body, gen_push_int(int(len(bench_start) / 2) + 33))
    assert len(res) / 2 <= MAX_CONTRACT_SIZE, "benchmark greater than max contract size"
    return res, inner_loop_evmmax_op_count

def gen_loop() -> str:
    return "{}7fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff015b{}60010180{}57"

def bench_geth_evmmax(arith_op_name: str, limb_count: int) -> (int, int):
    bench_code, evmmax_op_count = gen_arith_loop_benchmark(arith_op_name, limb_count)
    geth_exec = os.path.join(os.getcwd(), "go-ethereum/build/bin/evm")
    geth_cmd = "{} --code {} --bench run".format(geth_exec, bench_code)
    result = subprocess.run(geth_cmd.split(' '), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise Exception("geth exec error: {}".format(result.stderr))

    exec_time = str(result.stderr).split('\\n')[1].strip('execution time:  ')

    if exec_time.endswith("ms"):
        exec_time = int(float(exec_time[:-2]) * 1000000)
    elif exec_time.endswith("s"):
        exec_time = int(float(exec_time[:-1]) * 1000000 * 1000)
    else:
        raise Exception("unknown timestamp ending: {}".format(exec_time))

    return exec_time, evmmax_op_count

if __name__ == "__main__":
    #if len(sys.argv[1:]) != 2:
    #    raise Exception("must provide inputs op (MULMONTMAX,ADDMODMAX,SUBMODMAX) limbCount (1-11)")

    #op = sys.argv[1]
    #if op != "ADDMODMAX" and op != "SUBMODMAX" and op != "MULMONTMAX":
    #    raise Exception("unknown op")

    #limb_count = int(sys.argv[2])
    #if limb_count < 0 or limb_count > 11:
    #    raise Exception("must choose limb count between 1 and 11")

    for arith_op_name in ["ADDMODMAX", "SUBMODMAX", "MULMONTMAX"]:
        for limb_count in range(1,12):
            evmmax_bench_time, evmmax_op_count = bench_geth_evmmax(arith_op_name, limb_count) 

            push3_pop_bench_time = 0 # TODO bench_geth_push3_pop(evmmax_op_count)
            setmod_est_time = 0 # TODO

            est_time = (evmmax_bench_time - push3_pop_bench_time - setmod_est_time) / evmmax_op_count
            print("{} - {} limbs - {} ns/op".format(arith_op_name, limb_count, est_time))
