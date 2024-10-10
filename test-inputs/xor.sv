module FullAdder(input logic a, b, cin,
                 output logic sum, cout);

    logic temp1;
    
    assign temp1 = a ^ b | (~b);
    assign cout = temp1 | a ^ ( ~b | a);
    assign sum = temp1 ^ cin & cout;
    
endmodule
