module xorInPlace (
    input logic a,
    input logic b,
    input logic c,
    input logic d,
    input logic e,
    output logic y,output logic z);

    assign y =  (a ^ b ^ (c & e) ^ (d & e));
    assign z = a & e;
endmodule
