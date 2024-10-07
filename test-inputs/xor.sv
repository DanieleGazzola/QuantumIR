module FullAdder(input logic a, b, cin,
                 output logic sum, cout);

    logic temp1;
    
    assign cout = ~a & b;
    assign temp1 = ~cout & ~a;
    assign sum = a & cin;
    
endmodule
