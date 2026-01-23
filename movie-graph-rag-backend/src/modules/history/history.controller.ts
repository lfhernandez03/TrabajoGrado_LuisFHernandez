import { Controller, Get, UseGuards, Request, Param } from '@nestjs/common';
import { AuthGuard } from '@nestjs/passport';
import { ApiBearerAuth, ApiTags, ApiOperation } from '@nestjs/swagger';
import { HistoryService } from './history.service';

@ApiTags('history')
@ApiBearerAuth()
@Controller('history')
@UseGuards(AuthGuard('jwt'))
export class HistoryController {
  constructor(private readonly historyService: HistoryService) {}

  @Get('me')
  @ApiOperation({ summary: 'Obtener mi historial de recomendaciones' })
  async getMyHistory(@Request() req: { user: { userId: string } }) {
    return this.historyService.findByUser(req.user.userId);
  }

  @Get(':id')
  @ApiOperation({ summary: 'Obtener detalle de una consulta histórica' })
  async getDetail(@Param('id') id: string) {
    return this.historyService.findOne(id);
  }
}
