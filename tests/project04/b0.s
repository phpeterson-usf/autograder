main:
    add r0, r1, r2
    b foo
    add r1, r2, r0
foo:
    add r3, r2, r1
    bx lr
