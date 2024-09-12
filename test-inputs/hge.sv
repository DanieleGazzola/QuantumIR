module FullAdder(input logic a, b,
                 output logic sum, cout);

    logic temp1,temp2;

    assign temp1 = a ^ b;
    assign temp2 = a ^ b;
    assign sum = temp1 & temp2;
    assign cout = temp1 ^ sum;

endmodule