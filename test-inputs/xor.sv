module Module(input logic a, b,
                 output logic out1, out2);
    logic temp1;

    assign out1 = ~a & b;
    assign temp1 = a ^ b;

    assign out2 = a & ~temp1;
    
    
endmodule



