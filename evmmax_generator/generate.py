
MAX_LIMBS = 11

PUSH3_POP_ITER_COUNT = 0
EVMMAX_ARITH_ITER_COUNT = 0
raise Exception("TODO^")

EVMMAX_ARITH_OPS = {
    "ADDMODMAX": {},
    "SUBMODMAX": {},
    "MULMONTMAX": {},
}

def gen_push_word(item: int) -> str:
    pass

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

def gen_evmmax_op_loop_body(op: str, num_iterations: int) -> str:
    pass

def gen_push3_pop_loop_body(num_iterations: int) -> str:
    result = ""
    for i in range(num_iterations):
        result += gen_push3_zero() + gen_pop()

def gen_push3_pop_loop_benchmark() -> str:
    return gen_loop().format(gen_push3_pop_loop_body(PUSH3_POP_ITER_COUNT))

def gen_loop() -> str:
    return "7fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff01{}60010180602157"

def gen_arith_loop_benchmark(op: str) -> str:
    pass

def main():
    for op_name in EVMMAX_OPS.keys():
        with open("benchmarks/{}-loop.hex", "w") as f:
            f.write(gen_arith_loop_benchmark(op_name))

    with open("benchmarks/push3-pop-loop.hex", "w") as f:
        f.write(gen_push3_pop_loop_benchmark())

if __name__ == "__main__":
    main()
