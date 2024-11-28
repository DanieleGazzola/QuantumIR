module RemoveUnusedExample(
    input  logic a, b,
    output logic out1
);

    logic temp1;
    
    assign temp1 = a ^ b;
    assign out1 = a & b;
    
        
endmodule