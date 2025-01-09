module xorInPlace (
    input  logic a, b, c, d, e,
    output logic y, z
);

    assign y =  (a ^ b ^ (c & e) ^ (d & e));
    assign z = a & e;

endmodule
