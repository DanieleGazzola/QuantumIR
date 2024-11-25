module FullAdder(input logic a, b,c,
                 output logic out);

    logic temp1,temp2;

    assign temp1 = a ^ b;
    assign temp1 = a ^ b;
    assign out = a & temp1;

endmodule