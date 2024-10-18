module xorInPlace (
    input logic a,
    input logic b,
    input logic c,
    output logic y
);
    logic temp1;

    assign y =  ~a ^ b ^ c;
endmodule
