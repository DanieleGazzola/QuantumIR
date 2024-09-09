module FullAdder(input logic a, b, cin,
                 output logic sum, cout);

    logic temp1, temp2, temp3, temp4, temp5;

    assign temp1 = a ^ b;

    assign temp2 = (a ^ b) & cin;

    assign temp3 = a & b;

    assign sum = temp1 ^ temp2;

    assign temp4 = a ^ cin;

    assign temp5 = temp4 & cin;

    assign cout = temp3 | temp5;

endmodule