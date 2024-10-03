module FullAdder(input logic a, b, cin,
                 output logic sum, cout);

    logic temp1, temp2;

    assign cout = ~a ^ b;
    assign temp1 = cout ^ ~cout;
    assign temp2 = ~(b & ~cout);
    assign sum = ~temp1 & temp2 & cout;
    
endmodule
