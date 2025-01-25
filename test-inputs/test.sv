module Test(
    input  logic a, b, c,
    output logic out1, out2
);
    logic temp1;

    assign temp1 =a & b;
    assign out1 = c & temp1;
    assign out2 = (a & b) & temp1;

endmodule