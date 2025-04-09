module greater (
    input logic a0, a1, b0, b1,
    output logic gt
);
    assign gt = (a1 & ~b1) | ((a1 ~^ b1) & a0 & ~b0);
endmodule
