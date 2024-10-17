module xorInPlace (
    input logic a,
    input logic b,
    input logic c,
    input logic d,
    output logic y,
    output logic z
);
    logic temp1;

    assign temp1 = a & b;
    assign y =  a ^ b ^ c;
    assign z = a & temp1 & c;

endmodule
