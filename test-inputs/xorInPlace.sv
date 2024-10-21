module xorInPlace (
    input logic a,
    input logic b,
    input logic c,
    wire f,
    input logic d,
    output logic y,
    output logic z
);
    logic temp1;

    assign y =  ~(a ^ b ^ ~(c & d));
    assign z = c;
endmodule
