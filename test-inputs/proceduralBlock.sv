module proceduralBlock(input logic a, b,c,d,
                 output logic out);

    logic temp1;

    always_comb begin
        temp1 = a & c | a;
        out = ~temp1 & (b ^ c ^ d);
    end


endmodule



