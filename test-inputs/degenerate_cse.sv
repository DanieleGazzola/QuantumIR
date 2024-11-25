module CseTransformation(input logic a, b,c,
                output logic out1,out2);

    assign out1 = a & b;
    assign out2 = (a & b) ^ (a & b);

endmodule