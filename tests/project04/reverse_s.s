.global reverse_s

@ r0 points to a C string we want to reverse

reverse_s:
    mov r1, r0          @ use r1 for the end. init to the input string
find_end:               @ get a pointer to the last char in the string
    ldrb r2, [r1]       @ r2 = *r1
    cmp r2, #0          @ are we at the '\0'?
    beq reverse_1       @ if so, break out of the loop
    add r1, r1, #1      @ end += 1
    b find_end          @ loop
reverse_1:
    sub r1, r1, #1      @ back up one char from the '\0'
reverse_loop:
    cmp r0, r1          @ has the input ptr met the end ptr?
    bge end             @ if so, break out of the loop
    ldrb r2, [r0]       @ r2 is btmp
    ldrb r3, [r1]       @ r3 is etmp
    strb r2, [r1]       @ *end = btmp
    strb r3, [r0]       @ *buf = etmp
    add r0, r0, #1      @ buf++
    sub r1, r1, #1      @ end++
    b reverse_loop
end:    
    bx lr
