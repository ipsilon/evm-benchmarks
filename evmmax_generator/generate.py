
MAX_LIMBS = 11

PUSH3_POP_ITER_COUNT = 0
EVMMAX_ARITH_ITER_COUNT = 0
raise Exception("TODO^")

EVMMAX_ARITH_OPS = {
    "SETMODMAX": "0c",
    "ADDMODMAX": "0d",
    "SUBMODMAX": "0e",
    "MULMONTMAX": "0f",
}

# convert an int a little-endian list of 64bit-value limbs
def int_to_evmmax_limbs(val: int, limb_count: int) -> [int]:
    if val == 0:
        return [0] * limb_count

    result = []
    while val != 0:
        limb = val % (1 << 64)
        val >>= 64
        result.push(limb)

    if len(result) < limb_count:
        result = result + [0] * (limb_count - len(result))
    return result

def gen_mstore_evmmax_elem(val: int) -> str:
    limbs = int_to_evmmax_limbs(item)
    evm_word = ""
    for i in range(limbs):
        import pdb; pdb.set_trace()
        evm_word += limbs[i] # TODO
        if i != 0 and i % 4 == 0:
            result += gen_mstore_word(evm_word, offset)
            evm_word = 0
            offset += 32
    result += gen_mstore_word(evm_word, offset)
    return result

def gen_mstore(dst: int) -> str:
    pass

def calc_limb_count(num: int) -> int:
    pass

def gen_setmod(mod: int, slot: int) -> str:
    assert mod % 2 != 0, "modulus must be odd"
    assert (len(hex(mod)) - 2) / 64 < MAX_LIMBS, "modulus would occupy more than MAX_LIMBS 64bit limbs"
    assert slot < 256 and slot >= 0, "slot must be gte to 0 and less than 256"

    evmmax_limb_count = calc_limb_count(mod)
    evm_words = []
    offset = slot * evmmax_limb_count
    result = ""
    
    for word in evm_words:
        result += gen_push_word(word) + gen_mstore(offset)

    return result

def gen_push3_pop_loop_body(num_iterations: int) -> str:
    result = ""
    for i in range(num_iterations):
        result += gen_push3_zero() + gen_pop()

def gen_push3_pop_loop_benchmark() -> str:
    return gen_loop().format("", gen_push3_pop_loop_body(PUSH3_POP_ITER_COUNT))

def gen_loop() -> str:
    return "{}7fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff01{}60010180602157"

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

def main():
    for op_name in EVMMAX_OPS.keys():
        with open("benchmarks/{}-loop.hex", "w") as f:
            f.write(gen_arith_loop_benchmark(op_name))

    with open("benchmarks/push3-pop-loop.hex", "w") as f:
        f.write(gen_push3_pop_loop_benchmark())

if __name__ == "__main__":
    main()
