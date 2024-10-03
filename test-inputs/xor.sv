module FullAdder(input logic a, b, cin,
                 output logic sum, cout);

    logic temp1, temp2;

    assign temp1 = ~(a ^ b);
    assign cout = temp1 ^ ~a;
    assign temp2 = ~(b | ~a) | (~a | cin);
    assign sum = ~cout & temp2;
    
endmodule
