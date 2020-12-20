quadratic_a:
    mul r12, r0, r0
    mul r1, r1, r12
    mul r2, r0, r2
    add r0, r1, r2
    add r0, r0, r3
    bx lr
