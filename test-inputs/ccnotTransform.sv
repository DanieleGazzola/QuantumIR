module ccnotTransform(
    input logic a, b,c,d,
    output logic out1,out2);

    assign out1 = (a & d);
    assign out2 = b ^ c;
endmodule