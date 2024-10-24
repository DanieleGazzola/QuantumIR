module xorInPlace (
    input logic a,
    input logic b,
    input logic c,
    input logic d,
    output logic y,
    output logic z);

    assign y =  ~(a ^ b ^ ~(c & d) ^ b);
    assign z = c & (a ^ b);
    
endmodule
