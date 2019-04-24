module SRAM2048x64single #(
    parameter WIDTH=64,
    parameter ADDR_WIDTH=14
)(
    Q, CLK, CEB, BWEB, WEB, A, D, RTSEL, WTSEL
);

output reg [WIDTH-1:0] Q;
input        CLK;
input        CEB;
input        WEB;
input [ADDR_WIDTH-1:0]  A;
input [WIDTH-1:0] D;
input [WIDTH-1:0] BWEB;

input [1:0]  RTSEL;
input [1:0]  WTSEL;

reg[WIDTH-1:0] test_sig;

reg [WIDTH-1:0]   data_array [0:2**ADDR_WIDTH-1];
   
integer i;
always @(posedge CLK) begin
    if (CEB == 1'b0) begin                  // ACTIVE LOW!!
        Q = data_array[A];
        if (WEB == 1'b0) begin
            for(i=0; i<WIDTH; i=i+1) begin
                if (~BWEB[i] == 1) data_array[A][i] = D[i];  // ACTIVE LOW!!
            end
        end
        test_sig = data_array[A];
    end
end

endmodule