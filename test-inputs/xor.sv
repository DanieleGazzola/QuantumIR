module FullAdder(input logic a, b, cin,
                 output logic sum, cout);

    logic temp1;
    
    assign temp1 = a ^ b;
    assign cout = (a | b) ^ (b & temp1);
    assign sum = ~a & cin;
    
endmodule
