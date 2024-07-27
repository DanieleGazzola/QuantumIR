module FullAdder(input logic a, b, cin,
                 output logic sum, cout);

    logic xor_1, and_1, and_2;
    
    assign xor_1 = a ^ b;
    assign sum = xor_1 ^ cin;

    assign and_1 = a & b;
    assign and_2 = xor_1 & cin;
    assign cout = and_1 | and_2;
    
endmodule