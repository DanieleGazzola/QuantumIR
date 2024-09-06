module FullAdder(input logic a, b, cin,
                 output logic sum, cout);

    logic temp1,temp2;

    assign sum = a ^ (b ^ cin);

    assign cout = b ^ cin;

endmodule