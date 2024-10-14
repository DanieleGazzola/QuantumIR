module FullAdder(input logic a, b, cin,
                 output logic sum, cout);
    
    assign cout = a ^ ( ~b | a);
    assign sum = cin & cout;
    
endmodule
