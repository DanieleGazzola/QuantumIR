module FullAdder(input logic a, b, cin,
                 output logic sum, cout);

    logic temp1, temp2, temp3, temp4;

    assign temp4 = a ^ b ;

    assign temp1 = a ^ b;

    assign temp2 = a & b;

    assign sum = temp1 ^ cin;

    assign temp3 = temp1 & cin;

    assign cout = temp2 | temp3;

endmodule