module mux2to1 (
    input logic a, b, sel,
    output logic out
);
    assign out = (a & ~sel) | (b & sel);
endmodule
