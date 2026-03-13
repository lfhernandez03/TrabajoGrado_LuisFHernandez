/* eslint-disable @typescript-eslint/no-unsafe-assignment */
/* eslint-disable @typescript-eslint/no-unsafe-call */
import {
  Body,
  Controller,
  Delete,
  Get,
  Post,
  Request,
  UseGuards,
} from '@nestjs/common';
import { AuthGuard } from '@nestjs/passport';
import {
  ApiBearerAuth,
  ApiBody,
  ApiOperation,
  ApiResponse,
  ApiTags,
} from '@nestjs/swagger';
import { UsersService } from './users.service';
import {
  FavoriteMovieDto,
  FavoritesResponseDto,
  RemoveFavoriteDto,
} from './dto/favorite.dto';

@ApiTags('users')
@ApiBearerAuth()
@Controller('users')
@UseGuards(AuthGuard('jwt'))
export class UsersController {
  constructor(private readonly usersService: UsersService) {}

  @Get('me/favorites')
  @ApiOperation({ summary: 'Obtener favoritos del usuario autenticado' })
  @ApiResponse({ status: 200, type: FavoritesResponseDto })
  async getMyFavorites(
    @Request() req: { user: { userId: string } },
  ): Promise<FavoritesResponseDto> {
    const favorites = await this.usersService.getFavorites(req.user.userId);
    return { favorites };
  }

  @Post('me/favorites')
  @ApiOperation({ summary: 'Agregar película a favoritos' })
  @ApiBody({ type: FavoriteMovieDto })
  @ApiResponse({ status: 201, type: FavoritesResponseDto })
  async addFavorite(
    @Request() req: { user: { userId: string } },
    @Body() body: FavoriteMovieDto,
  ): Promise<FavoritesResponseDto> {
    const favorites = await this.usersService.addFavorite(
      req.user.userId,
      body,
    );
    return { favorites };
  }

  @Delete('me/favorites')
  @ApiOperation({ summary: 'Eliminar película de favoritos' })
  @ApiBody({ type: RemoveFavoriteDto })
  @ApiResponse({ status: 200, type: FavoritesResponseDto })
  async removeFavorite(
    @Request() req: { user: { userId: string } },
    @Body() body: RemoveFavoriteDto,
  ): Promise<FavoritesResponseDto> {
    const favorites = await this.usersService.removeFavorite(
      req.user.userId,
      body.uri,
    );
    return { favorites };
  }
}
