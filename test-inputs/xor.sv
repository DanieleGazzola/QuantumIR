module FullAdder(input logic a, b, cin,
                 output logic sum, cout);

    logic temp1;

    assign sum = a ^ ~b;
    assign cout = (a | b);
    
endmodule
