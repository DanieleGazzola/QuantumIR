module FullAdder(input logic a, b, cin,
                 output logic sum, cout);

    logic temp1, temp2;

    assign temp1 = a ^ b;
    assign temp2 = ~a;
    assign cout = temp2 & temp1;
    assign sum = b | cin;
    
endmodule
