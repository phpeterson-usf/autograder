main:
    add r0, r1, r2
    b foo
foo:
    add r3, r2, r1
    bx lr
